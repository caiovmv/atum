"""FastAPI app do Download Runner: GET/POST /downloads, start, stop, delete, stream, torrent metadata."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel


def _json_serial(value):
    """Converte valores do row para tipos JSON-serializáveis (PostgreSQL retorna datetime, Decimal)."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row_to_dict(row: dict) -> dict:
    out = {k: _json_serial(v) for k, v in row.items()}
    # Le = total de peers - seeders (para exibir "Se/Le" corretamente)
    num_peers = row.get("num_peers")
    num_seeds = row.get("num_seeds")
    if num_peers is not None and num_seeds is not None:
        out["num_leechers"] = max(0, int(num_peers) - int(num_seeds))
    else:
        out["num_leechers"] = None
    return out

# Importação relativa ao app (runner roda como processo separado com src no path)
from ..deps import get_settings, get_repo
from ..torrent_metadata import fetch_torrent_metadata
from ..download_manager import (
    add as dm_add,
    delete as dm_delete,
    list_downloads as dm_list,
    retry as dm_retry,
    start as dm_start,
    stop as dm_stop,
)

app = FastAPI(title="dl-torrent Download Runner", version="0.1.0")


class AddDownloadBody(BaseModel):
    magnet: str | None = None
    torrent_url: str | None = None
    save_path: str | None = None
    name: str | None = None
    content_type: str | None = None
    start_now: bool = True
    excluded_file_indices: list[int] | None = None
    torrent_files: list[dict] | None = None


@app.get("/downloads")
def list_downloads(status: str | None = None) -> list[dict]:
    """Lista downloads; status opcional: queued, downloading, paused, completed, failed."""
    rows = dm_list(status_filter=status)
    return [_row_to_dict(r) for r in rows]


_KEEPALIVE_INTERVAL = 30.0


async def _stream_downloads_events(status: str | None = None):
    """Generator SSE: Pub/Sub + polling adaptativo.

    Escuta eventos do CHANNEL_DOWNLOADS para reagir a mudanças de estado.
    Mantém polling adaptativo como garantia para progresso contínuo.
    Envia apenas quando os dados mudam (delta detection via hash).
    """
    import hashlib

    last_hash = ""

    async def _snapshot():
        nonlocal last_hash
        rows = await asyncio.to_thread(dm_list, status_filter=status)
        data = [_row_to_dict(r) for r in rows]
        current_hash = hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
        if current_hash != last_hash:
            last_hash = current_hash
            return f"data: {json.dumps(data)}\n\n"
        return None

    try:
        initial = await _snapshot()
        if initial:
            yield initial

        from ..event_bus import CHANNEL_DOWNLOADS, async_subscribe
        sub_task = None
        event_queue: asyncio.Queue[bool] = asyncio.Queue()

        async def _listen():
            try:
                async for channel, _ in async_subscribe(CHANNEL_DOWNLOADS, keepalive_interval=_KEEPALIVE_INTERVAL):
                    if channel:
                        await event_queue.put(True)
            except (asyncio.CancelledError, GeneratorExit):
                pass

        sub_task = asyncio.create_task(_listen())
        keepalive_counter = 0

        while True:
            try:
                await asyncio.wait_for(event_queue.get(), timeout=2.0)
                while not event_queue.empty():
                    event_queue.get_nowait()
            except asyncio.TimeoutError:
                pass

            msg = await _snapshot()
            if msg:
                yield msg
                keepalive_counter = 0
            else:
                keepalive_counter += 1
                if keepalive_counter >= 15:
                    yield ": keepalive\n\n"
                    keepalive_counter = 0

    except (asyncio.CancelledError, GeneratorExit):
        pass
    finally:
        if sub_task and not sub_task.done():
            sub_task.cancel()


@app.get("/downloads/events")
async def downloads_events(status: str | None = None):
    """SSE: stream de lista de downloads (atualização ~1s). Cliente usa EventSource."""
    return StreamingResponse(
        _stream_downloads_events(status),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/downloads/{download_id}")
def get_download(download_id: int) -> dict:
    """Retorna um download por id."""
    row = get_repo().get(download_id)
    if not row:
        raise HTTPException(status_code=404, detail="Download não encontrado.")
    return _row_to_dict(row)


@app.post("/downloads")
def add_download(body: AddDownloadBody) -> dict:
    """Adiciona um download à fila. save_path vazio usa LIBRARY_MUSIC_PATH ou LIBRARY_VIDEOS_PATH por content_type."""
    magnet = (body.magnet or "").strip()
    torrent_url = (body.torrent_url or "").strip()
    if not magnet and not torrent_url:
        raise HTTPException(status_code=400, detail="Informe magnet ou torrent_url.")
    # Garante que o campo magnet nunca fique vazio no DB (fallback para torrent_url)
    magnet_for_db = magnet or torrent_url
    s = get_settings()
    path = (body.save_path or "").strip()
    if not path:
        path = s.save_path_for_content_type(body.content_type)
    else:
        path = str(Path(path).expanduser().resolve())
    did = dm_add(
        magnet_for_db,
        path,
        name=body.name,
        content_type=body.content_type,
        excluded_file_indices=body.excluded_file_indices,
        torrent_files=body.torrent_files,
        torrent_url=torrent_url or None,
    )
    if did <= 0:
        raise HTTPException(status_code=500, detail="Erro ao adicionar à fila.")
    if body.start_now:
        dm_start(did)
    return {"id": did, "save_path": path, "started": body.start_now}


@app.post("/downloads/{download_id}/start")
def start_download(download_id: int) -> dict:
    """Inicia (ou retoma) um download em background."""
    if dm_start(download_id):
        return {"id": download_id, "started": True}
    raise HTTPException(
        status_code=404,
        detail="ID não encontrado ou download já em andamento/concluído.",
    )


@app.post("/downloads/{download_id}/stop")
def stop_download(download_id: int) -> dict:
    """Para um download em andamento."""
    if dm_stop(download_id):
        return {"id": download_id, "stopped": True}
    raise HTTPException(status_code=404, detail="ID não encontrado.")


@app.post("/downloads/{download_id}/retry")
def retry_download(download_id: int) -> dict:
    """Re-tenta um download falhado (reseta status, re-usa magnet/torrent_url persistidos)."""
    if dm_retry(download_id):
        return {"id": download_id, "retried": True}
    raise HTTPException(
        status_code=404,
        detail="ID não encontrado ou download não está em status 'failed'.",
    )


@app.delete("/downloads/{download_id}")
def delete_download(download_id: int, remove_files: bool = False) -> dict:
    """Remove um download da lista; remove_files=True apaga também os arquivos."""
    if dm_delete(download_id, remove_files=remove_files):
        return {"id": download_id, "deleted": True}
    raise HTTPException(status_code=404, detail="ID não encontrado.")


MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".m4v", ".mp3", ".flac", ".m4a", ".ogg", ".wav"}


def _list_media_files(content_path: str) -> list[dict]:
    """Lista todos os arquivos de mídia em content_path (recursivo, ordenado). Retorna [{index, name, size}, ...]."""
    p = Path(content_path)
    if not p.exists():
        return []
    if p.is_file():
        return [{"index": 0, "name": p.name, "size": p.stat().st_size}]
    files: list[Path] = []
    for f in sorted(p.rglob("*")):
        if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS:
            files.append(f)
    return [{"index": i, "name": f.name, "size": f.stat().st_size} for i, f in enumerate(files)]


def _list_all_files(content_path: str) -> list[dict]:
    """Lista todos os arquivos em content_path (recursivo, ordenado). Retorna [{index, name, size, is_media}, ...]."""
    p = Path(content_path)
    if not p.exists():
        return []
    if p.is_file():
        ext = p.suffix.lower()
        return [{"index": 0, "name": p.name, "size": p.stat().st_size, "is_media": ext in MEDIA_EXTENSIONS}]
    files: list[Path] = []
    for f in sorted(p.rglob("*")):
        if f.is_file():
            files.append(f)
    return [
        {"index": i, "name": f.name, "size": f.stat().st_size, "is_media": f.suffix.lower() in MEDIA_EXTENSIONS}
        for i, f in enumerate(files)
    ]


def _media_path_at_index(content_path: str, file_index: int | None) -> Path | None:
    """Retorna o primeiro arquivo de mídia (file_index=None) ou o arquivo no índice file_index."""
    p = Path(content_path)
    if not p.exists():
        return None
    if p.is_file():
        return p if (file_index is None or file_index == 0) else None
    files = sorted(f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS)
    if not files:
        return None
    if file_index is None:
        return files[0]
    if file_index < 0 or file_index >= len(files):
        return None
    return files[file_index]


class TorrentMetadataBody(BaseModel):
    magnet: str | None = None
    torrent_url: str | None = None


@app.post("/torrent/metadata")
def get_torrent_metadata(body: TorrentMetadataBody) -> dict:
    """Retorna nome e lista de arquivos do torrent. Aceita magnet ou torrent_url.
    Usa torrent_resolver para resolução com fallback (torrent_url -> magnet)."""
    from ..torrent_resolver import cleanup_temp_file, resolve_torrent_input
    from ..torrent_metadata import parse_torrent_bytes

    magnet = (body.magnet or "").strip() or None
    torrent_url = (body.torrent_url or "").strip() or None

    if not magnet and not torrent_url:
        raise HTTPException(
            status_code=400,
            detail="Informe magnet ou torrent_url (URL do arquivo .torrent).",
        )

    # Tentar via resolver (torrent_url primeiro, fallback magnet)
    temp_path: str | None = None
    try:
        resolved_input, temp_path = resolve_torrent_input(
            magnet=magnet, torrent_url=torrent_url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        # Se resolveu para arquivo .torrent (temp_path != None), parsear diretamente
        if temp_path:
            with open(temp_path, "rb") as f:
                data = f.read()
            result = parse_torrent_bytes(data)
            if result is None:
                raise HTTPException(
                    status_code=502,
                    detail="Não foi possível ler o arquivo .torrent baixado.",
                )
            return result

        # Resolveu para magnet: usar DHT para obter metadados
        if resolved_input.startswith("magnet:"):
            timeout_seconds = 120
            result = fetch_torrent_metadata(resolved_input, timeout_seconds=timeout_seconds)
            if result is None:
                result = fetch_torrent_metadata(resolved_input, timeout_seconds=timeout_seconds)
            if result is None:
                raise HTTPException(
                    status_code=504,
                    detail="Timeout ou falha ao obter metadados do magnet. Tente novamente.",
                )
            return result

        # Resolveu para path local de .torrent
        with open(resolved_input, "rb") as f:
            data = f.read()
        result = parse_torrent_bytes(data)
        if result is None:
            raise HTTPException(
                status_code=502,
                detail="Não foi possível ler o arquivo .torrent.",
            )
        return result
    finally:
        cleanup_temp_file(temp_path)


def _media_type_for_path(path: Path) -> str:
    """Retorna o media type adequado para o navegador reproduzir."""
    suf = path.suffix.lower()
    if suf in (".mp4", ".m4v", ".mov"):
        return "video/mp4"
    if suf == ".webm":
        return "video/webm"
    if suf in (".mkv", ".avi"):
        return "video/x-matroska" if suf == ".mkv" else "video/x-msvideo"
    if suf in (".mp3", ".m4a"):
        return "audio/mpeg" if suf == ".mp3" else "audio/mp4"
    if suf == ".flac":
        return "audio/flac"
    if suf == ".ogg":
        return "audio/ogg"
    if suf == ".wav":
        return "audio/wav"
    return "application/octet-stream"


def _stored_torrent_files_with_is_media(stored: list[dict]) -> list[dict]:
    """Adiciona is_media a cada item da lista persistida (por extensão do path)."""
    out = []
    for f in stored:
        item = dict(f)
        path = (item.get("path") or "").strip()
        ext = Path(path).suffix.lower() if path else ""
        item["is_media"] = ext in MEDIA_EXTENSIONS
        out.append(item)
    return out


@app.get("/downloads/{download_id}/files")
def list_download_files(download_id: int, all: bool = False) -> dict:
    """Lista arquivos do download (completed com content_path).
    Se houver torrent_files persistida, retorna essa lista (com is_media).
    Senão: all=False (padrão) = apenas mídia; all=True = todos no disco com is_media."""
    row = get_repo().get(download_id)
    if not row:
        raise HTTPException(status_code=404, detail="Download não encontrado.")
    if (row.get("status") or "").lower() != "completed":
        raise HTTPException(status_code=400, detail="Download não está concluído.")
    content_path = (row.get("content_path") or "").strip()
    stored = row.get("torrent_files")
    if isinstance(stored, list) and stored and content_path:
        files = _stored_torrent_files_with_is_media(stored)
        return {"download_id": download_id, "files": files}
    if not content_path:
        raise HTTPException(status_code=400, detail="Conteúdo não disponível.")
    if all:
        files = _list_all_files(content_path)
    else:
        files = _list_media_files(content_path)
    return {"download_id": download_id, "files": files}


@app.get("/downloads/{download_id}/file-path")
def get_download_file_path(download_id: int, file_index: int = 0) -> dict:
    """Retorna o caminho absoluto de um arquivo do download (usado pelo HLS service da API)."""
    row = get_repo().get(download_id)
    if not row:
        raise HTTPException(status_code=404, detail="Download não encontrado.")
    if (row.get("status") or "").lower() != "completed":
        raise HTTPException(status_code=400, detail="Download não está concluído.")
    content_path = (row.get("content_path") or "").strip()
    if not content_path:
        raise HTTPException(status_code=400, detail="Conteúdo não disponível.")
    path = None
    stored = row.get("torrent_files")
    if isinstance(stored, list) and 0 <= file_index < len(stored):
        rel = (stored[file_index].get("path") or "").strip()
        if rel:
            full = Path(content_path) / rel
            if full.is_file():
                path = full
    if path is None:
        path = _media_path_at_index(content_path, file_index)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return {"path": str(path), "name": path.name, "suffix": path.suffix.lower()}


@app.get("/downloads/{download_id}/stream")
def stream_download(download_id: int, file_index: int | None = None):
    """Serve um arquivo do download. file_index=N: índice na lista (torrent_files se existir, senão lista de mídia). Omitir = primeiro."""
    row = get_repo().get(download_id)
    if not row:
        raise HTTPException(status_code=404, detail="Download não encontrado.")
    if (row.get("status") or "").lower() != "completed":
        raise HTTPException(status_code=400, detail="Download não está concluído.")
    content_path = (row.get("content_path") or "").strip()
    if not content_path:
        raise HTTPException(status_code=400, detail="Conteúdo não disponível.")
    path = None
    stored = row.get("torrent_files")
    if isinstance(stored, list) and file_index is not None and 0 <= file_index < len(stored):
        # Resolver pelo path do torrent: content_path / path relativo do arquivo
        rel = (stored[file_index].get("path") or "").strip()
        if rel:
            full = Path(content_path) / rel
            if full.is_file():
                path = full
    if path is None:
        path = _media_path_at_index(content_path, file_index)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    media_type = _media_type_for_path(path)
    return FileResponse(str(path), media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})


def _content_path_allowed(content_path: str) -> bool:
    """True se content_path está dentro de LIBRARY_MUSIC_PATH ou LIBRARY_VIDEOS_PATH."""
    s = get_settings()
    try:
        resolved = Path(content_path).resolve()
        for base in (s.library_music_path, s.library_videos_path):
            if not (base or "").strip():
                continue
            base_resolved = Path(base.strip()).expanduser().resolve()
            try:
                resolved.relative_to(base_resolved)
                return True
            except ValueError:
                continue
    except Exception as exc:
        logging.getLogger(__name__).debug("Erro ao verificar content_path '%s': %s", content_path, exc)
    return False


@app.get("/library-import/files")
def list_library_import_files(content_path: str = ""):
    """Lista arquivos de mídia em content_path (itens importados). content_path deve estar em Library Music/Videos."""
    content_path = (content_path or "").strip()
    if not content_path or not _content_path_allowed(content_path):
        raise HTTPException(status_code=400, detail="content_path inválido ou fora da biblioteca.")
    files = _list_media_files(content_path)
    return {"content_path": content_path, "files": files}


@app.get("/library-import/stream")
def stream_library_import(content_path: str = "", file_index: int | None = None):
    """Serve um arquivo de mídia em content_path (itens importados). file_index opcional (0-based)."""
    content_path = (content_path or "").strip()
    if not content_path or not _content_path_allowed(content_path):
        raise HTTPException(status_code=400, detail="content_path inválido ou fora da biblioteca.")
    path = _media_path_at_index(content_path, file_index)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo de mídia não encontrado.")
    media_type = _media_type_for_path(path)
    return FileResponse(str(path), media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})
