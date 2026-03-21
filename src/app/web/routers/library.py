"""Rotas da Biblioteca: listar downloads + itens importados (pastas existentes), detalhe, stream."""

from __future__ import annotations

import asyncio
import hashlib
import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from ...deps import get_library_import_repo, get_settings
from ..hls_service import (
    ensure_transcoding,
    evict_caches,
    get_job,
    hls_file_path,
    invalidate_all_for_item,
    invalidate_cache,
    is_playable,
    master_manifest_path,
)

logger = __import__("logging").getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
    return _client


_stream_client: httpx.AsyncClient | None = None


def _get_stream_client() -> httpx.AsyncClient:
    """Client para streaming de mídia: sem read timeout (arquivos grandes em disco lento)."""
    global _stream_client
    if _stream_client is None or _stream_client.is_closed:
        _stream_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout=None, connect=10.0)
        )
    return _stream_client


class LibraryImportUpdateBody(BaseModel):
    """Campos opcionais para PATCH /api/library/imported/{id}."""

    name: str | None = None
    year: int | None = None
    artist: str | None = None
    album: str | None = None
    genre: str | None = None
    tags: list[str] | None = None

router = APIRouter(prefix="/library", tags=["library"])


_KEEPALIVE_INTERVAL = 30.0


async def _stream_library_events():
    """Generator SSE: escuta Redis Pub/Sub para eventos da biblioteca (enrichment, sync, edição)."""
    from ...event_bus import CHANNEL_LIBRARY, async_subscribe
    try:
        async for channel, data in async_subscribe(CHANNEL_LIBRARY, keepalive_interval=_KEEPALIVE_INTERVAL):
            if channel:
                payload: dict = {"event": "library_updated"}
                if data.get("facets_dirty"):
                    payload["facets_dirty"] = True
                if data.get("covers_dirty"):
                    payload["covers_dirty"] = data["covers_dirty"]
                yield f"data: {json.dumps(payload)}\n\n"
            else:
                yield ": keepalive\n\n"
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get("/events")
async def library_events():
    """SSE: stream de eventos da biblioteca via Redis Pub/Sub."""
    return StreamingResponse(
        _stream_library_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _runner_url(path: str) -> str:
    base = (get_settings().download_runner_url or "").rstrip("/")
    if not base:
        raise HTTPException(
            status_code=503,
            detail="DOWNLOAD_RUNNER_URL não configurado. Inicie o Runner: dl-torrent runner",
        )
    return f"{base}{path}"


def get_all_library_items() -> list[dict]:
    """Retorna todos os itens da biblioteca (downloads + imports) com content_path. Para uso interno (ex.: rádio)."""
    try:
        r = httpx.get(_runner_url("/downloads"), timeout=15)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner indisponível: {e}") from e
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    data = r.json()
    out = data if isinstance(data, list) else []
    for x in out:
        x["source"] = "download"
    import_repo = get_library_import_repo()
    if import_repo:
        for row in import_repo.list(content_type=None, artist=None, album=None, genre=None, tags=None):
            cp = (row.get("content_path") or "").strip()
            if not cp or not Path(cp).exists():
                continue
            out.append({
                "id": row["id"],
                "source": "import",
                "name": row.get("name") or "",
                "content_type": (row.get("content_type") or "music").strip() or "music",
                "content_path": cp,
                "cover_path_small": row.get("cover_path_small"),
                "cover_path_large": row.get("cover_path_large"),
                "year": row.get("year"),
                "artist": row.get("artist"),
                "album": row.get("album"),
                "genre": row.get("genre"),
                "tags": row.get("tags") or [],
            })
    return [x for x in out if (x.get("content_path") or "").strip()]


def _parent_path(p: str) -> str:
    """Retorna o diretório pai do path (normalizado com /)."""
    s = (p or "").strip().replace("\\", "/").rstrip("/")
    if "/" not in s:
        return ""
    return s[: s.rfind("/")]


@router.get("")
async def list_library(
    request: Request,
    content_type: str | None = Query(None, description="Filtrar por tipo: music, movies, tv, concerts"),
    q: str | None = Query(None, description="Busca full-text (nome, artista, álbum, gênero, moods, descriptors, overview…)"),
    artist: str | None = Query(None, description="Filtrar por artista"),
    album: str | None = Query(None, description="Filtrar por álbum"),
    genre: str | None = Query(None, description="Filtrar por gênero"),
    tag: list[str] = Query(default_factory=list, description="Filtrar por tag; múltiplos = qualquer"),
    mood: str | None = Query(None, description="Filtrar por mood (enrichment)"),
    sub_genre: str | None = Query(None, description="Filtrar por sub-gênero (enrichment)"),
    descriptor: str | None = Query(None, description="Filtrar por descriptor (enrichment)"),
    bpm_min: float | None = Query(None, description="BPM mínimo (enrichment)"),
    bpm_max: float | None = Query(None, description="BPM máximo (enrichment)"),
    folder_path: str | None = Query(None, description="Filtrar por pasta (dirname do content_path)"),
    limit: int | None = Query(None, ge=1, le=500, description="Máximo de itens a retornar"),
    offset: int | None = Query(None, ge=0, description="Pular N itens"),
):
    """Lista itens da biblioteca: downloads concluídos + itens importados. Busca via PostgreSQL FTS."""
    ct = content_type.strip().lower() if (content_type or "").strip() in ("music", "movies", "tv", "concerts") else None
    tags_list = [t.strip() for t in tag if (t or "").strip()] or None

    async def _fetch_downloads():
        try:
            from ...deps import get_repo
            repo = get_repo()
            if repo and hasattr(repo, 'list'):
                try:
                    rows = await asyncio.to_thread(
                        lambda: repo.list(status_filter="completed", q=q, content_type=ct, limit=limit, offset=offset)
                    )
                except TypeError:
                    rows = await asyncio.to_thread(lambda: repo.list(status_filter="completed"))
                for x in rows:
                    x["source"] = "download"
                return rows
        except Exception:
            pass
        try:
            client = _get_client()
            r = await client.get(_runner_url("/downloads"))
            raw = r.json() if r.status_code == 200 and isinstance(r.json(), list) else []
            for x in raw:
                x["source"] = "download"
            return raw
        except Exception:
            return []

    folder_path_norm = folder_path.strip() if (folder_path or "").strip() else None
    if folder_path_norm:
        folder_path_norm = folder_path_norm.replace("\\", "/").rstrip("/")

    async def _fetch_imports():
        import_repo = get_library_import_repo()
        if not import_repo:
            return []
        return await asyncio.to_thread(
            lambda: list(import_repo.list(
                content_type=ct,
                artist=artist, album=album, genre=genre,
                tags=tags_list, q=q,
                mood=mood, sub_genre=sub_genre, descriptor=descriptor,
                bpm_min=bpm_min, bpm_max=bpm_max,
                folder_path=folder_path_norm,
                limit=limit, offset=offset,
            ))
        )

    downloads_raw, import_rows = await asyncio.gather(_fetch_downloads(), _fetch_imports())

    out: list[dict] = []
    for x in downloads_raw:
        x.setdefault("source", "download")
        if folder_path_norm:
            cp = (x.get("content_path") or "").strip()
            if cp and _parent_path(cp) != folder_path_norm:
                continue
        out.append(x)

    for row in import_rows:
        cp = (row.get("content_path") or "").strip()
        if not cp or not Path(cp).exists():
            continue
        item: dict = {
            "id": row["id"],
            "source": "import",
            "name": row.get("name") or "",
            "content_type": (row.get("content_type") or "music").strip() or "music",
            "content_path": cp,
            "cover_path_small": row.get("cover_path_small"),
            "cover_path_large": row.get("cover_path_large"),
            "year": row.get("year"),
            "artist": row.get("artist"),
            "album": row.get("album"),
            "genre": row.get("genre"),
            "tags": row.get("tags") or [],
            "tmdb_id": row.get("tmdb_id"),
            "imdb_id": row.get("imdb_id"),
        }
        for ek in (
            "bpm", "musical_key", "energy", "danceability", "valence",
            "sub_genres", "moods", "descriptors", "record_label", "release_type",
            "overview", "vote_average", "runtime_minutes", "tmdb_genres",
            "enriched_at", "enrichment_sources",
        ):
            v = row.get(ek)
            if v is not None:
                item[ek] = v
        out.append(item)

    body = json.dumps(out, default=str, ensure_ascii=False)
    etag = hashlib.md5(body.encode()).hexdigest()
    if request.headers.get("if-none-match") == f'"{etag}"':
        return Response(status_code=304)
    return Response(content=body, media_type="application/json", headers={"ETag": f'"{etag}"', "Cache-Control": "private, max-age=0, must-revalidate"})


class DownloadTagsBody(BaseModel):
    """Tags para PATCH /api/library/{id}/tags."""
    tags: list[str]


@router.patch("/{download_id}/tags")
def update_download_tags(download_id: int, body: DownloadTagsBody) -> dict:
    """Atualiza tags customizadas de um download."""
    from ...deps import get_repo
    repo = get_repo()
    if not repo:
        raise HTTPException(status_code=503, detail="Repositório não disponível.")
    row = repo.get(download_id)
    if not row:
        raise HTTPException(status_code=404, detail="Download não encontrado.")
    tags = [str(t).strip() for t in body.tags if str(t).strip()]
    if hasattr(repo, "update_tags"):
        repo.update_tags(download_id, tags)
    else:
        raise HTTPException(status_code=501, detail="Operação não suportada neste backend.")
    from ...event_bus import CACHE_FACETS_PREFIX, CHANNEL_LIBRARY, cache_delete_pattern, publish
    publish(CHANNEL_LIBRARY, {"type": "item_updated", "ids": [download_id], "facets_dirty": True})
    cache_delete_pattern(f"{CACHE_FACETS_PREFIX}:*")
    return {"id": download_id, "tags": tags}


@router.get("/imported/{import_id}")
def get_library_imported_item(import_id: int) -> dict:
    """Detalhe de um item importado (pasta existente em Library Music/Videos)."""
    import_repo = get_library_import_repo()
    if not import_repo:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    row = import_repo.get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    cp = (row.get("content_path") or "").strip()
    if not cp or not Path(cp).exists():
        raise HTTPException(status_code=404, detail="Conteúdo não disponível.")
    item_data: dict = {
        "id": row["id"],
        "source": "import",
        "name": row.get("name") or "",
        "content_type": (row.get("content_type") or "music").strip() or "music",
        "content_path": cp,
        "cover_path_small": row.get("cover_path_small"),
        "cover_path_large": row.get("cover_path_large"),
        "year": row.get("year"),
        "artist": row.get("artist"),
        "album": row.get("album"),
        "genre": row.get("genre"),
        "tags": row.get("tags") or [],
    }
    for ek in (
        "bpm", "musical_key", "energy", "danceability", "valence",
        "sub_genres", "moods", "descriptors", "record_label", "release_type",
        "overview", "vote_average", "runtime_minutes", "tmdb_genres",
        "original_title", "backdrop_path", "musicbrainz_id",
        "enriched_at", "enrichment_sources",
        "user_edited_at", "cover_source",
    ):
        v = row.get(ek)
        if v is not None:
            item_data[ek] = v
    return item_data


@router.get("/imported/{import_id}/detail")
async def get_library_imported_detail(import_id: int) -> dict:
    """Detalhe completo: item + files + folder_stats + metadata_json (ffprobe) + cover_source."""
    import_repo = get_library_import_repo()
    if not import_repo:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    row = await asyncio.to_thread(import_repo.get, import_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    cp = (row.get("content_path") or "").strip()
    if not cp or not Path(cp).exists():
        raise HTTPException(status_code=404, detail="Conteúdo não disponível.")

    folder_path = Path(cp)
    folder_stats: dict | None = None
    try:
        stat = folder_path.stat()
        folder_stats = {
            "path": str(folder_path),
            "parent": str(folder_path.parent),
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime,
        }
    except OSError:
        pass

    files_data: dict | None = None
    try:
        url = _runner_url("/library-import/files") + "?" + urllib.parse.urlencode({"content_path": cp})
        client = _get_client()
        r = await client.get(url)
        if r.status_code == 200:
            files_data = r.json()
    except Exception:
        pass

    metadata_json = row.get("metadata_json")
    if isinstance(metadata_json, str):
        try:
            metadata_json = json.loads(metadata_json)
        except json.JSONDecodeError:
            metadata_json = None

    return {
        "id": row["id"],
        "source": "import",
        "name": row.get("name") or "",
        "content_type": (row.get("content_type") or "music").strip() or "music",
        "content_path": cp,
        "cover_path_small": row.get("cover_path_small"),
        "cover_path_large": row.get("cover_path_large"),
        "cover_source": row.get("cover_source"),
        "year": row.get("year"),
        "artist": row.get("artist"),
        "album": row.get("album"),
        "genre": row.get("genre"),
        "tags": row.get("tags") or [],
        "user_edited_at": row.get("user_edited_at"),
        "folder_stats": folder_stats,
        "files": files_data,
        "metadata_json": metadata_json,
    }


@router.get("/autocomplete")
def get_library_autocomplete(
    q: str | None = Query(None, description="Termo de busca (prefixo)"),
    content_type: str | None = Query(None, description="music, movies, tv ou concerts"),
    limit: int = Query(10, ge=1, le=30),
) -> dict:
    """Sugestões de autocomplete: artist, album, title, genre. Usa FTS em library_imports e downloads."""
    term = (q or "").strip()
    if not term:
        return {"suggestions": []}
    ct = (content_type or "").strip().lower() if content_type else None
    if ct and ct not in ("music", "movies", "tv", "concerts"):
        ct = None

    terms = term.split()
    tsquery = " & ".join(t + ":*" for t in terms if t)
    if not tsquery:
        return {"suggestions": []}

    from ...db_postgres import connection_postgres
    from ...config import get_settings

    settings = get_settings()
    db_url = settings.database_url
    if not db_url:
        return {"suggestions": []}

    per_type = max(2, limit // 4)
    suggestions: list[dict] = []

    ct_clause = " AND content_type = %s" if ct else ""
    dl_extra = " AND status = 'completed'"  # só downloads concluídos
    params_base = [tsquery] + ([ct] if ct else [])

    def run_query(table: str, col: str, stype: str, extra: str = "") -> list[dict]:
        with connection_postgres(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT DISTINCT TRIM({col}) AS v
                    FROM {table}
                    WHERE search_vector @@ to_tsquery('simple', %s)
                      AND {col} IS NOT NULL AND TRIM({col}) != ''
                    {ct_clause}{extra}
                    ORDER BY v
                    LIMIT %s
                    """,
                    params_base + [per_type],
                )
                return [{"type": stype, "value": r["v"], "count": None} for r in cur.fetchall()]

    try:
        for table, col, stype in [
            ("library_imports", "artist", "artist"),
            ("library_imports", "album", "album"),
            ("library_imports", "name", "title"),
            ("library_imports", "genre", "genre"),
        ]:
            suggestions.extend(run_query(table, col, stype))
        for table, col, stype in [
            ("downloads", "artist", "artist"),
            ("downloads", "album", "album"),
            ("downloads", "name", "title"),
            ("downloads", "genre", "genre"),
        ]:
            suggestions.extend(run_query(table, col, stype, dl_extra))
    except Exception:
        return {"suggestions": []}

    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for s in suggestions:
        key = (s["type"], (s["value"] or "").strip())
        if key in seen or not key[1]:
            continue
        seen.add(key)
        deduped.append(s)
        if len(deduped) >= limit:
            break
    return {"suggestions": deduped}


@router.get("/folders")
def get_library_folders(
    content_type: str | None = Query(None, description="music, movies, tv ou concerts"),
) -> dict:
    """Lista pastas (dirname de content_path) com contagem. Retorna {folders: [{path, name, count}]}."""
    ct = (content_type or "").strip().lower() if content_type else None
    if ct and ct not in ("music", "movies", "tv", "concerts"):
        ct = None
    import_repo = get_library_import_repo()
    if not import_repo:
        return {"folders": []}
    folders = import_repo.list_folders(content_type=ct or None)
    return {"folders": folders}


@router.get("/facets")
def get_library_facets(
    request: Request,
    content_type: str | None = Query(None, description="music, movies, tv ou concerts para facetas daquele tipo"),
):
    """Listas de artistas, álbums, gêneros e tags para filtrar/agrupar a biblioteca (imports + downloads). Cache Redis 1h + ETag."""
    from ...event_bus import CACHE_FACETS_PREFIX, cache_get, cache_set
    ct = (content_type or "").strip().lower() if content_type else None
    if ct and ct not in ("music", "movies", "tv", "concerts"):
        ct = None
    cache_key = f"{CACHE_FACETS_PREFIX}:{ct or 'all'}"
    cached = cache_get(cache_key)
    if cached is not None:
        result = cached
    else:
        import_repo = get_library_import_repo()
        if not import_repo:
            result = {"artists": [], "albums": [], "genres": [], "tags": [], "moods": [], "sub_genres": [], "descriptors": []}
        else:
            result = import_repo.get_facets(content_type=ct or None)

        try:
            dl_facets = _get_download_facets(ct)
            for key in ("artists", "albums", "genres"):
                existing = set(result.get(key, []))
                for v in dl_facets.get(key, []):
                    if v and v not in existing:
                        result.setdefault(key, []).append(v)
                        existing.add(v)
                result[key] = sorted(result.get(key, []), key=str.lower)
        except Exception:
            pass

        cache_set(cache_key, result, ttl_seconds=3600)
    body = json.dumps(result, default=str, ensure_ascii=False)
    etag = hashlib.md5(body.encode()).hexdigest()
    if request.headers.get("if-none-match") == f'"{etag}"':
        return Response(status_code=304)
    return Response(content=body, media_type="application/json", headers={"ETag": f'"{etag}"', "Cache-Control": "private, max-age=0, must-revalidate"})


def _get_download_facets(content_type: str | None) -> dict:
    """Extrai artistas, álbuns e gêneros distintos dos downloads concluídos."""
    try:
        from ...config import get_settings
        from ...db_postgres import connection_postgres
        db_url = get_settings().database_url
        if not db_url:
            return {}
        ct_clause = ""
        params: list = []
        if content_type:
            ct_clause = " AND content_type = %s"
            params.append(content_type)
        with connection_postgres(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT DISTINCT artist FROM downloads WHERE artist IS NOT NULL AND status = 'completed'{ct_clause} ORDER BY artist",
                    params,
                )
                artists = [r["artist"] for r in cur.fetchall()]
                cur.execute(
                    f"SELECT DISTINCT album FROM downloads WHERE album IS NOT NULL AND status = 'completed'{ct_clause} ORDER BY album",
                    params,
                )
                albums = [r["album"] for r in cur.fetchall()]
                cur.execute(
                    f"SELECT DISTINCT genre FROM downloads WHERE genre IS NOT NULL AND status = 'completed'{ct_clause} ORDER BY genre",
                    params,
                )
                genres = [r["genre"] for r in cur.fetchall()]
        return {"artists": artists, "albums": albums, "genres": genres}
    except Exception:
        return {}


@router.patch("/imported/{import_id}")
def update_library_imported_item(import_id: int, body: LibraryImportUpdateBody) -> dict:
    """Atualiza metadados de um item importado. Campos opcionais: name, year, artist, album, genre, tags (array)."""
    import_repo = get_library_import_repo()
    if not import_repo:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    row = import_repo.get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    cp = (row.get("content_path") or "").strip()
    if not cp or not Path(cp).exists():
        raise HTTPException(status_code=404, detail="Conteúdo não disponível.")
    b = body.model_dump(exclude_unset=True)
    updates: dict[str, Any] = {}
    if "name" in b and b["name"] is not None:
        updates["name"] = str(b["name"]).strip() or row.get("name")
    if "year" in b:
        v = b["year"]
        updates["year"] = int(v) if v is not None and str(v).strip() != "" else None
    if "artist" in b:
        updates["artist"] = str(b["artist"]).strip() if b["artist"] is not None else None
    if "album" in b:
        updates["album"] = str(b["album"]).strip() if b["album"] is not None else None
    if "genre" in b:
        updates["genre"] = str(b["genre"]).strip() if b["genre"] is not None else None
    if "tags" in b:
        tags = b["tags"]
        updates["tags"] = [str(t).strip() for t in tags] if isinstance(tags, list) else []
    if not updates:
        return {
            "id": row["id"],
            "source": "import",
            "name": row.get("name") or "",
            "content_type": (row.get("content_type") or "music").strip() or "music",
            "content_path": cp,
            "cover_path_small": row.get("cover_path_small"),
            "cover_path_large": row.get("cover_path_large"),
            "year": row.get("year"),
            "artist": row.get("artist"),
            "album": row.get("album"),
            "genre": row.get("genre"),
            "tags": row.get("tags") or [],
        }
    updates["user_edited_at"] = datetime.now(timezone.utc).isoformat()
    import_repo.update_metadata(import_id, **updates)
    from ...event_bus import CACHE_FACETS_PREFIX, CHANNEL_LIBRARY, cache_delete_pattern, publish
    facets_dirty = any(k in updates for k in ("genre", "artist", "album", "tags"))
    publish(CHANNEL_LIBRARY, {"type": "item_updated", "ids": [import_id], "facets_dirty": facets_dirty})
    if facets_dirty:
        cache_delete_pattern(f"{CACHE_FACETS_PREFIX}:*")
    row = import_repo.get(import_id) or row
    return {
        "id": row["id"],
        "source": "import",
        "name": row.get("name") or "",
        "content_type": (row.get("content_type") or "music").strip() or "music",
        "content_path": cp,
        "cover_path_small": row.get("cover_path_small"),
        "cover_path_large": row.get("cover_path_large"),
        "year": row.get("year"),
        "artist": row.get("artist"),
        "album": row.get("album"),
        "genre": row.get("genre"),
        "tags": row.get("tags") or [],
    }


@router.get("/imported/{import_id}/files")
async def list_library_imported_files(import_id: int) -> dict:
    """Lista arquivos de mídia do item importado."""
    import_repo = get_library_import_repo()
    if not import_repo:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    row = await asyncio.to_thread(import_repo.get, import_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    cp = (row.get("content_path") or "").strip()
    if not cp or not Path(cp).exists():
        raise HTTPException(status_code=404, detail="Conteúdo não disponível.")
    url = _runner_url("/library-import/files") + "?" + urllib.parse.urlencode({"content_path": cp})
    client = _get_client()
    r = await client.get(url)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    data = r.json()
    data["download_id"] = None
    data["import_id"] = import_id
    return data


@router.get("/imported/{import_id}/stream")
async def stream_library_imported_item(
    import_id: int,
    file_index: int | None = Query(None, description="Índice do arquivo (0-based)"),
):
    """Proxy do stream do item importado (Runner serve por content_path)."""
    import_repo = get_library_import_repo()
    if not import_repo:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    row = await asyncio.to_thread(import_repo.get, import_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    cp = (row.get("content_path") or "").strip()
    if not cp or not Path(cp).exists():
        raise HTTPException(status_code=404, detail="Conteúdo não disponível.")
    url = _runner_url("/library-import/stream") + "?" + urllib.parse.urlencode({"content_path": cp})
    if file_index is not None:
        url += "&" + urllib.parse.urlencode({"file_index": file_index})
    client = _get_stream_client()
    try:
        req = client.build_request("GET", url)
        resp = await client.send(req, stream=True)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner: {e}") from e
    if resp.status_code != 200:
        body = await resp.aread()
        await resp.aclose()
        raise HTTPException(status_code=resp.status_code, detail=body.decode(errors="replace") or "Erro ao obter stream")

    async def _stream():
        try:
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                yield chunk
        finally:
            await resp.aclose()

    return StreamingResponse(
        _stream(),
        media_type=resp.headers.get("content-type") or "application/octet-stream",
    )


class RefreshCoverBody(BaseModel):
    """Corpo opcional para POST /api/library/.../refresh-cover."""
    query: str | None = None


ALLOWED_COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_COVER_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/imported/{import_id}/cover-upload")
async def upload_imported_cover(import_id: int, file: UploadFile = File(...)) -> dict:
    """Upload manual de capa para item importado. Aceita JPG, PNG, WebP (até 5 MB)."""
    import_repo = get_library_import_repo()
    if not import_repo:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    row = import_repo.get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item não encontrado.")

    fn = (file.filename or "").strip()
    ext = Path(fn).suffix.lower() if fn else ""
    if ext not in ALLOWED_COVER_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado. Use: {', '.join(ALLOWED_COVER_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_COVER_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande (máx. 5 MB).")

    s = get_settings()
    covers_path = s.covers_path
    covers_path.mkdir(parents=True, exist_ok=True)
    small_file = covers_path / f"import_{import_id}_small.jpg"
    large_file = covers_path / f"import_{import_id}_large.jpg"

    try:
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(content))
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(small_file, "JPEG", quality=85)
            img.save(large_file, "JPEG", quality=90)
        except ImportError:
            if ext in (".jpg", ".jpeg"):
                with open(small_file, "wb") as f:
                    f.write(content)
                with open(large_file, "wb") as f:
                    f.write(content)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Para PNG/WebP instale Pillow: pip install Pillow",
                ) from None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Imagem inválida: {e}") from e

    small_path = f"import_{import_id}_small.jpg"
    large_path = f"import_{import_id}_large.jpg"
    import_repo.update_metadata(
        import_id,
        cover_path_small=small_path,
        cover_path_large=large_path,
        cover_source="user",
    )
    from ...event_bus import CHANNEL_LIBRARY, publish
    publish(CHANNEL_LIBRARY, {"type": "cover_updated", "ids": [import_id], "covers_dirty": [import_id]})
    return {"ok": True, "cover_path_small": small_path, "cover_path_large": large_path}


@router.post("/imported/{import_id}/refresh-cover")
def refresh_imported_cover(import_id: int, body: RefreshCoverBody | None = None) -> dict:
    """Re-busca artwork de um item importado nos serviços de enriquecimento (TMDB, iTunes)."""
    import_repo = get_library_import_repo()
    if not import_repo:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    row = import_repo.get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item não encontrado.")

    from ..cover_service import get_cover_urls
    from ...sync_library_imports import _download_cover

    search_term = (body.query if body and body.query else None) or row.get("name") or ""
    content_type = (row.get("content_type") or "music").strip() or "music"
    item_name = (row.get("name") or "Item")[:60]

    urls = get_cover_urls(content_type, search_term)
    s = get_settings()
    covers_path = s.covers_path
    covers_path.mkdir(parents=True, exist_ok=True)

    small_path = None
    large_path = None
    if urls.url_small:
        small_file = covers_path / f"import_{import_id}_small.jpg"
        if _download_cover(urls.url_small, small_file):
            small_path = f"import_{import_id}_small.jpg"
    if urls.url_large and urls.url_large != urls.url_small:
        large_file = covers_path / f"import_{import_id}_large.jpg"
        if _download_cover(urls.url_large, large_file):
            large_path = f"import_{import_id}_large.jpg"
    elif small_path:
        large_path = small_path

    if small_path or large_path:
        cover_src = "itunes" if content_type == "music" else "tmdb"
        import_repo.update_metadata(
            import_id,
            cover_path_small=small_path,
            cover_path_large=large_path,
            cover_source=cover_src,
        )

    ok = bool(small_path or large_path)
    try:
        from ...db import notification_create
        if ok:
            notification_create("cover_refreshed", f"Capa atualizada: {item_name}")
        else:
            notification_create("cover_refresh_failed", f"Capa não encontrada: {item_name}", body=f"Termo: {search_term}")
    except Exception as exc:
        logger.debug("Falha ao criar notificação de capa (import): %s", exc)
    if ok:
        from ...event_bus import CHANNEL_LIBRARY, publish
        publish(CHANNEL_LIBRARY, {"type": "cover_updated", "ids": [import_id], "covers_dirty": [import_id]})

    updated_row = import_repo.get(import_id) or row
    return {
        "ok": ok,
        "cover_path_small": updated_row.get("cover_path_small"),
        "cover_path_large": updated_row.get("cover_path_large"),
        "search_term": search_term,
    }


@router.post("/{library_id}/refresh-cover")
async def refresh_download_cover(library_id: int, body: RefreshCoverBody | None = None) -> dict:
    """Re-busca artwork de um download da biblioteca nos serviços de enriquecimento."""
    client = _get_client()
    r = await client.get(_runner_url(f"/downloads/{library_id}"))
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    item = r.json()
    name = item.get("name") or ""
    item_name = (name or "Item")[:60]
    content_type = (item.get("content_type") or "music").strip() or "music"
    search_term = (body.query if body and body.query else None) or name

    from ..cover_service import evict_cover_for_download, fetch_and_cache_cover
    await asyncio.to_thread(evict_cover_for_download, library_id)
    urls = await asyncio.to_thread(fetch_and_cache_cover, library_id, content_type, search_term)

    ok = bool(urls.url_small or urls.url_large)
    try:
        from ...db import notification_create
        if ok:
            notification_create("cover_refreshed", f"Capa atualizada: {item_name}")
        else:
            notification_create("cover_refresh_failed", f"Capa não encontrada: {item_name}", body=f"Termo: {search_term}")
    except Exception as exc:
        logger.debug("Falha ao criar notificação de capa (download): %s", exc)

    return {
        "ok": ok,
        "url_small": urls.url_small,
        "url_large": urls.url_large,
        "search_term": search_term,
    }


@router.get("/{library_id}")
async def get_library_item(library_id: int) -> dict:
    """Detalhe de um item da biblioteca (download concluído com content_path)."""
    client = _get_client()
    r = await client.get(_runner_url(f"/downloads/{library_id}"))
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    item = r.json()
    if (item.get("status") or "").lower() != "completed":
        raise HTTPException(status_code=404, detail="Item não concluído.")
    if not (item.get("content_path") or "").strip():
        raise HTTPException(status_code=404, detail="Conteúdo não disponível.")
    return item


@router.get("/{library_id}/files")
async def list_library_files(library_id: int) -> dict:
    """Lista arquivos de mídia do item (para o usuário escolher o que reproduzir)."""
    url = _runner_url(f"/downloads/{library_id}/files")
    client = _get_client()
    r = await client.get(url)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.get("/{library_id}/stream")
async def stream_library_item(
    library_id: int,
    file_index: int | None = Query(None, description="Índice do arquivo (0-based); omitir = primeiro"),
):
    """Proxy do stream do arquivo de mídia (Runner serve o arquivo). Use file_index para escolher qual arquivo."""
    url = _runner_url(f"/downloads/{library_id}/stream")
    if file_index is not None:
        url = f"{url}?file_index={file_index}"
    client = _get_stream_client()
    try:
        req = client.build_request("GET", url)
        resp = await client.send(req, stream=True)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner: {e}") from e
    if resp.status_code != 200:
        body = await resp.aread()
        await resp.aclose()
        raise HTTPException(status_code=resp.status_code, detail=body.decode(errors="replace") or "Erro ao obter stream")

    async def _stream():
        try:
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                yield chunk
        finally:
            await resp.aclose()

    return StreamingResponse(
        _stream(),
        media_type=resp.headers.get("content-type") or "application/octet-stream",
    )


# ---------------------------------------------------------------------------
# HLS endpoints — streaming adaptativo via FFmpeg
# ---------------------------------------------------------------------------


@router.get("/{library_id}/hls/{file_index}/status")
async def hls_transcode_status(library_id: int, file_index: int = 0) -> dict:
    """Retorna o status da transcodificação HLS.

    status: "pending" | "processing" | "ready" | "error"
    """
    if master_manifest_path(library_id, file_index).exists():
        return {"status": "ready", "progress": 100}
    job = get_job(library_id, file_index)
    if job is None:
        return {"status": "pending", "progress": 0}
    return {
        "status": job.status,
        "progress": job.progress,
        "error_message": job.error,
    }


@router.get("/{library_id}/hls/{file_index}/{hls_path:path}")
async def hls_serve(library_id: int, file_index: int, hls_path: str) -> Response:
    """Serve arquivos HLS (master.m3u8, playlists de variante e segmentos .ts).

    Para master.m3u8: dispara a transcodificação FFmpeg se necessário.
    Retorna 202 Accepted + Retry-After: 3 enquanto o FFmpeg processa.
    """
    # Proteção contra path traversal
    try:
        resolved = hls_file_path(library_id, file_index, hls_path).resolve()
        base = master_manifest_path(library_id, file_index).parent.resolve()
        resolved.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Caminho HLS inválido.")

    if hls_path == "master.m3u8":
        job = await ensure_transcoding(library_id, file_index)
        if job.status == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Transcodificação HLS falhou: {job.error}",
            )
        # Reprodução progressiva: serve master.m3u8 assim que o primeiro segmento
        # de qualquer variante estiver disponível (~6–12 s após o início do FFmpeg).
        # O Shaka Player re-busca as playlists de variante automaticamente à medida
        # que novos segmentos chegam (behavior de HLS live), até ver #EXT-X-ENDLIST.
        if job.status != "ready" and not is_playable(library_id, file_index):
            return Response(
                status_code=202,
                headers={"Retry-After": "3", "Cache-Control": "no-store"},
            )

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Arquivo HLS não encontrado.")

    if hls_path.endswith(".m3u8"):
        media_type = "application/vnd.apple.mpegurl"
        # Playlists de variante crescem durante a transcodificação → nunca cachear
        # enquanto o job estiver em andamento (Shaka precisa re-buscar para ver novos
        # segmentos). Após a conclusão, podem ser cacheadas normalmente.
        job_now = get_job(library_id, file_index)
        cache_ctrl = (
            "no-store"
            if (job_now and job_now.status == "processing")
            else "public, max-age=3600"
        )
    elif hls_path.endswith(".ts"):
        media_type = "video/mp2t"
        # Segmentos são imutáveis — cache agressivo
        cache_ctrl = "public, max-age=86400"
    else:
        media_type = "application/octet-stream"
        cache_ctrl = "public, max-age=3600"

    return FileResponse(
        str(resolved),
        media_type=media_type,
        headers={"Cache-Control": cache_ctrl},
    )


@router.delete("/{library_id}/hls/{file_index}")
async def hls_delete_file_cache(library_id: int, file_index: int) -> dict:
    """Invalida e remove o cache HLS de um arquivo específico.

    Útil quando o arquivo fonte foi atualizado ou a transcodificação ficou
    corrompida. A próxima requisição a master.m3u8 re-transcodifica do zero.
    """
    had_cache = invalidate_cache(library_id, file_index)
    return {
        "invalidated": had_cache,
        "library_id": library_id,
        "file_index": file_index,
    }


@router.delete("/{library_id}/hls")
async def hls_delete_all_cache(library_id: int) -> dict:
    """Invalida e remove todo o cache HLS de um item da biblioteca (todos os arquivos).

    Use quando o item foi atualizado ou se o cache ocupar espaço excessivo.
    """
    count = invalidate_all_for_item(library_id)
    return {"invalidated_count": count, "library_id": library_id}


@router.post("/hls/evict")
async def hls_evict_caches(
    max_age_days: int = Query(30, ge=1, description="Remover caches com acesso mais antigo que N dias"),
    max_size_gb: float = Query(100.0, gt=0, description="Remover os mais antigos até ficar abaixo de N GB"),
) -> dict:
    """Evita que o volume HLS encha: remove caches antigos ou em excesso de tamanho.

    Política:
    - Caches com último acesso > max_age_days são sempre removidos.
    - Se tamanho total > max_size_gb, remove os mais antigos até ficar abaixo do limite.
    - Jobs em andamento nunca são removidos.

    Chamado pelo CronJob K8s diariamente (padrão: 30 dias / 100 GB).
    """
    result = evict_caches(max_age_days=max_age_days, max_size_gb=max_size_gb)
    return result
