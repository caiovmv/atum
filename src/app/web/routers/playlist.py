"""Rotas de Playlists, Favoritos e Contagem de Reproduções."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import tempfile
import urllib.parse
import zipfile
from pathlib import Path

import httpx
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from starlette.responses import FileResponse, RedirectResponse, StreamingResponse

logger = logging.getLogger(__name__)

from ...ai.prompts_registry import get_prompt_temperature, get_system_prompt
from ...config import get_settings
from ...deps import get_settings_repo
from ...repositories.playlist_repository_postgres import (
    add_tracks,
    check_favorites_batch,
    create_playlist,
    delete_playlist,
    get_most_played,
    get_playlist,
    get_playlist_tracks_with_paths,
    increment_play_count,
    list_playlists,
    remove_track,
    reorder_tracks,
    replace_tracks,
    reset_play_counts,
    toggle_favorite,
    update_playlist,
)

router = APIRouter(prefix="/playlists", tags=["playlists"])

AUDIO_EXTS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".wma", ".aac", ".opus", ".ape", ".wv"}


def _runner_url(path: str) -> str:
    base = (get_settings().download_runner_url or "").rstrip("/")
    return f"{base}{path}"


# ─── Playlists CRUD ───

@router.get("")
def api_list_playlists(kind: str | None = None) -> list[dict]:
    try:
        return list_playlists(kind=kind)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RuleBody(BaseModel):
    kind: str = "include"
    type: str = "content_type"
    value: str | dict | list


class PlaylistCreateBody(BaseModel):
    name: str
    kind: str = "static"
    rules: list[RuleBody] | None = None
    ai_prompt: str | None = None
    description: str | None = None


@router.post("")
def api_create_playlist(body: PlaylistCreateBody) -> dict:
    try:
        rules_dicts = None
        if body.rules:
            rules_dicts = [r.model_dump() for r in body.rules]
        pid = create_playlist(
            body.name,
            kind=body.kind,
            rules=rules_dicts,
            ai_prompt=body.ai_prompt,
            description=body.description,
        )
        return {"id": pid, "name": body.name.strip(), "kind": body.kind}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{playlist_id}")
def api_get_playlist(playlist_id: int) -> dict:
    try:
        p = get_playlist(playlist_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not p:
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    return p


class PlaylistUpdateBody(BaseModel):
    name: str | None = None
    cover_path: str | None = None
    rules: list[RuleBody] | None = None
    ai_prompt: str | None = None
    ai_notes: str | None = None
    description: str | None = None


@router.patch("/{playlist_id}")
def api_update_playlist(playlist_id: int, body: PlaylistUpdateBody) -> dict:
    try:
        rules_dicts = None
        if body.rules is not None:
            rules_dicts = [r.model_dump() for r in body.rules]
        ok = update_playlist(
            playlist_id,
            name=body.name,
            cover_path=body.cover_path,
            rules=rules_dicts,
            ai_prompt=body.ai_prompt,
            ai_notes=body.ai_notes,
            description=body.description,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    return {"id": playlist_id}


def _playlist_cover_dir() -> Path:
    """Diretório para capas das playlists (covers_path/playlists)."""
    d = get_settings().covers_path / "playlists"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _first_track_cover_url(p: dict) -> str | None:
    """Retorna URL da capa da primeira faixa com artwork, ou None."""
    tracks = p.get("tracks") or []
    covers_path = get_settings().covers_path
    for t in tracks:
        src = (t.get("source") or "").strip()
        item_id = t.get("item_id")
        if item_id is None:
            continue
        if src == "download":
            if (covers_path / f"{item_id}_small.jpg").is_file():
                return f"/api/cover/file/{item_id}?size=large"
        elif src == "import":
            cp = (t.get("cover_path_small") or "").strip()
            if cp and Path(cp).is_file():
                return f"/api/cover/file/import/{item_id}?size=large"
    return None


@router.get("/{playlist_id}/cover")
def api_playlist_cover(playlist_id: int):
    """Serve a capa da playlist: customizada ou fallback da primeira faixa com artwork."""
    p = get_playlist(playlist_id)
    if not p:
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    cover_path = (p.get("cover_path") or "").strip()
    if cover_path:
        full = get_settings().covers_path / cover_path
        if full.is_file():
            return FileResponse(full, media_type="image/jpeg")
    fallback = _first_track_cover_url(p)
    if fallback:
        return RedirectResponse(url=fallback, status_code=302)
    raise HTTPException(status_code=404, detail="Capa não definida.")


@router.post("/{playlist_id}/cover")
async def api_upload_playlist_cover(playlist_id: int, file: UploadFile = File(...)) -> dict:
    """Envia uma imagem como capa da playlist (substitui a anterior)."""
    p = get_playlist(playlist_id)
    if not p:
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    if p.get("system_kind"):
        raise HTTPException(status_code=400, detail="Playlists do sistema não podem ser editadas.")
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Envie um arquivo de imagem (JPEG, PNG, etc.).")
    ext = ".jpg"
    if "png" in content_type:
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"
    _MAX_COVER_BYTES = 5 * 1024 * 1024  # 5 MB
    dest_dir = _playlist_cover_dir()
    dest = dest_dir / f"{playlist_id}{ext}"
    try:
        data = await file.read(_MAX_COVER_BYTES + 1)
        if not data:
            raise HTTPException(status_code=400, detail="Arquivo vazio.")
        if len(data) > _MAX_COVER_BYTES:
            raise HTTPException(status_code=413, detail="Arquivo muito grande (máx 5 MB).")
        dest.write_bytes(data)
    except HTTPException:
        raise
    except OSError as e:
        logger.exception("Erro ao gravar capa da playlist")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {e}") from e
    except Exception as e:
        logger.exception("Erro inesperado no upload de capa")
        raise HTTPException(status_code=500, detail=str(e)) from e
    relative = f"playlists/{playlist_id}{ext}"
    try:
        update_playlist(playlist_id, cover_path=relative)
    except Exception as e:
        logger.exception("Erro ao atualizar cover_path no banco")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {e}") from e
    return {"id": playlist_id, "cover_path": relative}


@router.delete("/{playlist_id}")
def api_delete_playlist(playlist_id: int) -> dict:
    try:
        ok = delete_playlist(playlist_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")
    return {"id": playlist_id}


# ─── From Queue / Generate ───

class FromQueueTrack(BaseModel):
    id: int
    source: str = "download"
    file_index: int = 0
    file_name: str | None = None
    item_name: str | None = None
    artist: str | None = None


class FromQueueBody(BaseModel):
    name: str
    tracks: list[FromQueueTrack]
    description: str | None = None


@router.post("/from-queue")
def api_from_queue(body: FromQueueBody) -> dict:
    """Salva uma fila de reprodução (Smart Queue ou qualquer radioQueue) como playlist estática."""
    if not body.tracks:
        raise HTTPException(status_code=400, detail="Fila vazia.")
    try:
        pid = create_playlist(body.name, kind="static", description=body.description)
        tracks_dicts = [
            {
                "source": t.source,
                "item_id": t.id,
                "file_index": t.file_index,
                "file_name": t.file_name or t.item_name,
            }
            for t in body.tracks
        ]
        add_tracks(pid, tracks_dicts)
        return {"id": pid, "name": body.name.strip(), "track_count": len(body.tracks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_playlist_queue(playlist_id: int, limit: int = 500) -> list[dict]:
    """Gera fila de uma coleção dinâmica. Retorna tracks sem persistir. Usado por voice e api_generate."""
    try:
        p = get_playlist(playlist_id)
    except Exception:
        return []
    if not p:
        return []

    kind = p.get("kind", "static")
    if kind == "static":
        return []

    from .library import get_all_library_items
    from .radio import _filter_library_by_sintonia, _fetch_item_files

    if kind == "dynamic_rules":
        rules = p.get("rules") or []
        items = get_all_library_items()
        filtered = _filter_library_by_sintonia(items, rules)
        tracks: list[dict] = []
        for item in filtered:
            files = _fetch_item_files(item)
            item_name = (item.get("name") or "").strip() or "Sem nome"
            artist = (item.get("artist") or "").strip() or None
            for f in files:
                idx = f.get("index", 0)
                name = (f.get("name") or "").strip() or f"Faixa {idx + 1}"
                tracks.append({
                    "source": item.get("source") or "download",
                    "item_id": item["id"],
                    "file_index": idx,
                    "file_name": name,
                })
        random.shuffle(tracks)
        return tracks[:limit]

    if kind == "dynamic_ai":
        prompt = p.get("ai_prompt") or ""
        if not prompt:
            return []

        from ...ai.llm_client import LLMClient

        client = LLMClient.from_settings()
        if not client:
            return []

        items = get_all_library_items()
        # Heurística: extrair possível nome de artista do prompt (ex.: "Phil Collins Billboard" -> "Phil Collins")
        import re
        first_segment = prompt.split(" - ")[0].split(" na ")[0].strip()
        words = first_segment.split()
        skip_words = {"billboard", "top", "as", "the", "best", "greatest", "hits", "músicas", "songs"}
        artist_candidates = []
        for w in words:
            if w.lower() in skip_words:
                break
            if len(w) > 1 and w[0].isupper():
                artist_candidates.append(w)
        artist_hint = " ".join(artist_candidates[:3]) if artist_candidates else ""
        if artist_hint:
            filtered = [it for it in items if (it.get("artist") or "").lower().find(artist_hint.lower()) >= 0]
            if filtered:
                items = filtered
        items_to_send = items[:150]
        lib_lines: list[str] = []
        for item in items_to_send:
            parts = [f"ID={item.get('id')}: {item.get('name', '?')}"]
            if item.get("artist"):
                parts.append(f"by {item['artist']}")
            tags: list[str] = []
            if item.get("genre"):
                tags.append(item["genre"])
            if item.get("moods") and isinstance(item["moods"], list):
                tags.append(f"mood:{','.join(item['moods'][:3])}")
            if item.get("sub_genres") and isinstance(item["sub_genres"], list):
                tags.append(f"style:{','.join(item['sub_genres'][:2])}")
            if tags:
                parts.append(f"[{'; '.join(tags)}]")
            lib_lines.append(" ".join(parts))

        repo = get_settings_repo() or {"ai_prompts": {}}
        sys_prompt = get_system_prompt("playlist_ai", repo)
        temp = get_prompt_temperature("playlist_ai", repo)
        user_prompt = f"Pedido: {prompt}\n\nBiblioteca:\n" + "\n".join(lib_lines)
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            resp = await asyncio.to_thread(client.chat, messages, temp)
        except Exception:
            return []

        text = resp.content.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        selected_ids: list[int] = []
        explanation = ""
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
                selected_ids = [int(x) for x in (data.get("ids") or []) if isinstance(x, (int, float))]
                explanation = data.get("explanation", "")
            except (ValueError, json.JSONDecodeError):
                pass

        items_by_id = {item["id"]: item for item in items}
        queue_tracks: list[dict] = []
        for sid in selected_ids:
            item = items_by_id.get(sid)
            if not item:
                continue
            files = _fetch_item_files(item)
            source = item.get("source") or "download"
            if files:
                for f in files:
                    queue_tracks.append({
                        "source": source,
                        "item_id": sid,
                        "file_index": f.get("index", 0),
                        "file_name": (f.get("name") or "").strip() or None,
                    })
            else:
                queue_tracks.append({"source": source, "item_id": sid, "file_index": 0})

        if explanation:
            update_playlist(playlist_id, ai_notes=explanation)
        return queue_tracks[:limit]

    return []


@router.post("/{playlist_id}/generate")
async def api_generate(playlist_id: int, limit: int = Query(500, ge=1, le=500)) -> dict:
    """Gera/regenera a fila de uma coleção dinâmica (rules ou AI)."""
    try:
        p = get_playlist(playlist_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not p:
        raise HTTPException(status_code=404, detail="Coleção não encontrada.")

    kind = p.get("kind", "static")
    if kind == "static":
        raise HTTPException(status_code=400, detail="Playlists estáticas não podem ser regeneradas.")

    queue = await generate_playlist_queue(playlist_id, limit)
    if not queue:
        raise HTTPException(status_code=400, detail=f"Tipo de coleção desconhecido ou vazio: {kind}")

    count = replace_tracks(playlist_id, queue)
    return {"tracks": queue, "count": count}


# ─── Tracks ───

class TrackBody(BaseModel):
    source: str
    item_id: int
    file_index: int = 0
    file_name: str | None = None


class AddTracksBody(BaseModel):
    tracks: list[TrackBody]


@router.post("/{playlist_id}/tracks")
def api_add_tracks(playlist_id: int, body: AddTracksBody) -> dict:
    try:
        tracks = [t.model_dump() for t in body.tracks]
        count = add_tracks(playlist_id, tracks)
        return {"added": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{playlist_id}/tracks/{track_id}")
def api_remove_track(playlist_id: int, track_id: int) -> dict:
    try:
        ok = remove_track(playlist_id, track_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Track não encontrada.")
    return {"id": track_id}


class ReorderBody(BaseModel):
    track_ids: list[int]


@router.put("/{playlist_id}/tracks/reorder")
def api_reorder_tracks(playlist_id: int, body: ReorderBody) -> dict:
    try:
        reorder_tracks(playlist_id, body.track_ids)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Favoritos ───

class FavoriteToggleBody(BaseModel):
    source: str
    item_id: int
    file_index: int = 0
    file_name: str | None = None


@router.post("/favorites/toggle")
def api_toggle_favorite(body: FavoriteToggleBody) -> dict:
    try:
        added = toggle_favorite(body.source, body.item_id, body.file_index, body.file_name)
        return {"favorited": added}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FavoritesCheckBody(BaseModel):
    tracks: list[TrackBody]


@router.post("/favorites/check")
def api_check_favorites(body: FavoritesCheckBody) -> list[dict]:
    try:
        tracks = [t.model_dump() for t in body.tracks]
        return check_favorites_batch(tracks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Play Count ───

class PlayCountBody(BaseModel):
    source: str
    item_id: int
    file_index: int = 0


@router.post("/play-count/increment")
def api_increment_play_count(body: PlayCountBody) -> dict:
    try:
        count = increment_play_count(body.source, body.item_id, body.file_index)
        return {"play_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/play-count/reset")
def api_reset_play_counts() -> dict:
    try:
        deleted = reset_play_counts()
        return {"reset": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/play-count/top")
def api_top_played(limit: int = Query(100, ge=1, le=500)) -> list[dict]:
    try:
        return get_most_played(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Download / Export ───

def _resolve_track_files(track: dict) -> list[tuple[str, int]]:
    """Retorna lista de (caminho_absoluto, tamanho) para os arquivos de mídia de um track."""
    content_path = (track.get("content_path") or "").strip()
    if not content_path:
        return []

    fi = track.get("file_index", 0)

    torrent_files = track.get("torrent_files")
    if torrent_files and isinstance(torrent_files, str):
        try:
            torrent_files = json.loads(torrent_files)
        except (ValueError, TypeError):
            torrent_files = None

    p = Path(content_path)
    if p.is_file():
        return [(str(p), p.stat().st_size)]

    if not p.is_dir():
        return []

    audio_files = sorted(
        [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXTS],
        key=lambda f: f.name,
    )

    if torrent_files and isinstance(torrent_files, list):
        for tf in torrent_files:
            if isinstance(tf, dict) and tf.get("index") == fi:
                tf_path = tf.get("path", "")
                target = p / tf_path
                if target.is_file():
                    return [(str(target), target.stat().st_size)]
                break

    if 0 <= fi < len(audio_files):
        f = audio_files[fi]
        return [(str(f), f.stat().st_size)]

    if audio_files:
        f = audio_files[0]
        return [(str(f), f.stat().st_size)]

    return []


@router.get("/{playlist_id}/download/zip")
def api_download_zip(
    playlist_id: int,
    max_size_gb: int = Query(16, ge=1, le=128),
):
    """Cria zip sem compressão com os arquivos da playlist, limitado por max_size_gb."""
    try:
        tracks = get_playlist_tracks_with_paths(playlist_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not tracks:
        raise HTTPException(status_code=404, detail="Playlist vazia ou não encontrada.")

    max_bytes = max_size_gb * 1024 * 1024 * 1024
    files_to_zip: list[tuple[str, str]] = []
    total_size = 0
    seen_names: set[str] = set()

    for t in tracks:
        resolved = _resolve_track_files(t)
        for file_path, file_size in resolved:
            if total_size + file_size > max_bytes:
                break
            arc_name = Path(file_path).name
            if arc_name in seen_names:
                stem = Path(arc_name).stem
                ext = Path(arc_name).suffix
                arc_name = f"{stem}_{t.get('item_id', 0)}_{t.get('file_index', 0)}{ext}"
            seen_names.add(arc_name)
            files_to_zip.append((file_path, arc_name))
            total_size += file_size
        if total_size >= max_bytes:
            break

    if not files_to_zip:
        raise HTTPException(status_code=404, detail="Nenhum arquivo encontrado para esta playlist.")

    tmp_dir = tempfile.mkdtemp(prefix="atum-playlist-zip-")
    zip_path = os.path.join(tmp_dir, "playlist.zip")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for file_path, arc_name in files_to_zip:
            zf.write(file_path, arc_name)

    playlist_data = get_playlist(playlist_id)
    playlist_name = (playlist_data.get("name") if playlist_data else "playlist") or "playlist"
    safe_name = "".join(c for c in playlist_name if c.isalnum() or c in " _-").strip() or "playlist"

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{safe_name}.zip",
        background=None,
    )


@router.get("/{playlist_id}/download/m3u")
def api_download_m3u(playlist_id: int):
    """Exporta a playlist como arquivo .m3u8 com URLs de stream."""
    try:
        p = get_playlist(playlist_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not p:
        raise HTTPException(status_code=404, detail="Playlist não encontrada.")

    tracks = p.get("tracks") or []
    lines = ["#EXTM3U", f"#PLAYLIST:{p['name']}"]
    for t in tracks:
        title = t.get("file_name") or t.get("item_name") or "—"
        artist = t.get("artist") or ""
        source = t.get("source", "download")
        item_id = t.get("item_id")
        fi = t.get("file_index", 0)

        if source == "import":
            url = f"/api/library/imported/{item_id}/stream?file_index={fi}"
        else:
            url = f"/api/library/{item_id}/stream?file_index={fi}"

        display = f"{artist} - {title}" if artist else title
        lines.append(f"#EXTINF:-1,{display}")
        lines.append(url)

    content = "\n".join(lines) + "\n"

    playlist_name = p.get("name") or "playlist"
    safe_name = "".join(c for c in playlist_name if c.isalnum() or c in " _-").strip() or "playlist"

    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="audio/x-mpegurl",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.m3u8"'},
    )
