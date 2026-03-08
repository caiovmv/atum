"""Rotas da Biblioteca: listar downloads + itens importados (pastas existentes), detalhe, stream."""

from __future__ import annotations

import asyncio
import json
import urllib.parse
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...deps import get_library_import_repo, get_settings

logger = __import__("logging").getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
    return _client


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
    """Generator SSE: verifica marcador a cada ciclo; se mudou envia library_updated; keepalive a cada 30s."""
    import_repo = get_library_import_repo()
    last_marker: tuple[int, str | None] = (-1, None)
    try:
        while True:
            try:
                if import_repo:
                    marker = await asyncio.to_thread(import_repo.get_update_marker)
                else:
                    marker = (0, None)
            except Exception as exc:
                logger.warning("SSE library_events marker error: %s", exc)
                await asyncio.sleep(_KEEPALIVE_INTERVAL)
                continue
            if marker != last_marker:
                last_marker = marker
                yield f"data: {json.dumps({'event': 'library_updated'})}\n\n"
            await asyncio.sleep(_KEEPALIVE_INTERVAL)
            yield ": keepalive\n\n"
            await asyncio.sleep(_KEEPALIVE_INTERVAL)
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get("/events")
async def library_events():
    """SSE: stream de eventos de atualização da biblioteca (verificação a cada 60 s)."""
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


@router.get("")
async def list_library(
    content_type: str | None = Query(None, description="Filtrar por tipo: music, movies, tv"),
    q: str | None = Query(None, description="Busca no título/nome"),
    artist: str | None = Query(None, description="Filtrar por artista (imports)"),
    album: str | None = Query(None, description="Filtrar por álbum (imports)"),
    genre: str | None = Query(None, description="Filtrar por gênero (imports)"),
    tag: list[str] = Query(default_factory=list, description="Filtrar por tag (imports); múltiplos = qualquer"),
    mood: str | None = Query(None, description="Filtrar por mood (imports enrichment)"),
    sub_genre: str | None = Query(None, description="Filtrar por sub-gênero (imports enrichment)"),
    bpm_min: float | None = Query(None, description="BPM mínimo (imports enrichment)"),
    bpm_max: float | None = Query(None, description="BPM máximo (imports enrichment)"),
) -> list[dict]:
    """Lista itens da biblioteca: downloads concluídos (Runner) + itens importados (pastas em Library Music/Videos)."""
    client = _get_client()
    r = await client.get(
        _runner_url("/downloads"),
    )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    out = r.json() if isinstance(r.json(), list) else []
    for x in out:
        x["source"] = "download"
    import_repo = get_library_import_repo()
    if import_repo:
        tags_list = [t.strip() for t in tag if (t or "").strip()] or None
        for row in import_repo.list(
            content_type=content_type.strip().lower() if (content_type or "").strip() in ("music", "movies", "tv") else None,
            artist=artist,
            album=album,
            genre=genre,
            tags=tags_list,
            q=q,
            mood=mood,
            sub_genre=sub_genre,
            bpm_min=bpm_min,
            bpm_max=bpm_max,
        ):
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
    if content_type and (content_type or "").strip():
        ct = (content_type or "").strip().lower()
        if ct in ("music", "movies", "tv"):
            out = [x for x in out if (x.get("content_type") or "").strip().lower() == ct]
    if q and (q or "").strip():
        ql = (q or "").strip().lower()
        out = [x for x in out if ql in (
            (x.get("name") or "") + " " + (x.get("title") or "") + " " +
            (x.get("artist") or "") + " " + (x.get("album") or "")
        ).lower()]
    return out


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
    ):
        v = row.get(ek)
        if v is not None:
            item_data[ek] = v
    return item_data


@router.get("/facets")
def get_library_facets(
    content_type: str | None = Query(None, description="music, movies ou tv para facetas daquele tipo"),
) -> dict:
    """Listas de artistas, álbums, gêneros e tags para filtrar/agrupar a biblioteca."""
    import_repo = get_library_import_repo()
    if not import_repo:
        return {"artists": [], "albums": [], "genres": [], "tags": []}
    ct = (content_type or "").strip().lower() if content_type else None
    if ct and ct not in ("music", "movies", "tv"):
        ct = None
    return import_repo.get_facets(content_type=ct or None)


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
    import_repo.update_metadata(import_id, **updates)
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
    row = import_repo.get(import_id)
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
    row = import_repo.get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    cp = (row.get("content_path") or "").strip()
    if not cp or not Path(cp).exists():
        raise HTTPException(status_code=404, detail="Conteúdo não disponível.")
    url = _runner_url("/library-import/stream") + "?" + urllib.parse.urlencode({"content_path": cp})
    if file_index is not None:
        url += "&" + urllib.parse.urlencode({"file_index": file_index})
    client = _get_client()
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
            small_path = str(small_file)
    if urls.url_large and urls.url_large != urls.url_small:
        large_file = covers_path / f"import_{import_id}_large.jpg"
        if _download_cover(urls.url_large, large_file):
            large_path = str(large_file)
    elif small_path:
        large_path = small_path

    if small_path or large_path:
        import_repo.update_metadata(
            import_id,
            cover_path_small=small_path,
            cover_path_large=large_path,
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
    client = _get_client()
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
