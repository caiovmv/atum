"""FastAPI app do Download Runner: GET/POST /downloads, start, stop, delete."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Importação relativa ao app (runner roda como processo separado com src no path)
from ..deps import get_settings
from ..download_manager import (
    add as dm_add,
    delete as dm_delete,
    list_downloads as dm_list,
    start as dm_start,
    stop as dm_stop,
)

app = FastAPI(title="dl-torrent Download Runner", version="0.1.0")


class AddDownloadBody(BaseModel):
    magnet: str
    save_path: str | None = None
    name: str | None = None
    content_type: str | None = None
    start_now: bool = True


@app.get("/downloads")
def list_downloads(status: str | None = None) -> list[dict]:
    """Lista downloads; status opcional: queued, downloading, paused, completed, failed."""
    return dm_list(status_filter=status)


@app.post("/downloads")
def add_download(body: AddDownloadBody) -> dict:
    """Adiciona um download à fila. save_path vazio usa config (DOWNLOAD_DIR/watch_folder/downloads)."""
    s = get_settings()
    path = (
        (body.save_path or "").strip()
        or getattr(s, "download_dir", "")
        or getattr(s, "watch_folder", "")
        or "./downloads"
    )
    path = str(Path(path).expanduser().resolve())
    did = dm_add(
        body.magnet.strip(),
        path,
        name=body.name,
        content_type=body.content_type,
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


@app.delete("/downloads/{download_id}")
def delete_download(download_id: int, remove_files: bool = False) -> dict:
    """Remove um download da lista; remove_files=True apaga também os arquivos."""
    if dm_delete(download_id, remove_files=remove_files):
        return {"id": download_id, "deleted": True}
    raise HTTPException(status_code=404, detail="ID não encontrado.")
