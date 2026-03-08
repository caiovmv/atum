"""Rotas de Feeds: listar/adicionar/remover feeds, poll, pendentes, adicionar aos downloads."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...config import get_settings
from ...db import (
    add_feed_record,
    delete_feed_record,
    get_feed_by_id,
    list_feed_records,
    notification_create,
    pending_delete,
    pending_get,
    pending_list,
)
from ...feeds import poll_feeds_api
from ...organize import extract_subpath_by_content_type

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feeds", tags=["feeds"])


_KEEPALIVE_INTERVAL = 30.0


async def _stream_feed_events():
    """Generator SSE: a cada 30 s verifica feed_pending; se mudou envia evento; keepalive a cada 30s."""
    last_count = -1
    try:
        while True:
            pending = await asyncio.to_thread(pending_list)
            count = len(pending) if isinstance(pending, list) else 0
            if count != last_count:
                last_count = count
                yield f"data: {json.dumps({'event': 'feeds_pending_updated'})}\n\n"
            yield ": keepalive\n\n"
            await asyncio.sleep(_KEEPALIVE_INTERVAL)
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get("/events")
async def feed_events():
    """SSE: stream de eventos de atualização dos pendentes (verificação a cada 30 s)."""
    return StreamingResponse(
        _stream_feed_events(),
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


@router.get("")
def list_feeds() -> list[dict]:
    """Lista todos os feeds (id, url, title, content_type, created_at)."""
    return list_feed_records()


class AddFeedBody(BaseModel):
    url: str
    content_type: str = "music"


@router.post("")
def add_feed(body: AddFeedBody) -> dict:
    """Adiciona um feed RSS. content_type: music, movies, tv."""
    url = (body.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL não pode ser vazia.")
    ct = (body.content_type or "music").strip().lower()
    if ct not in ("music", "movies", "tv"):
        raise HTTPException(status_code=400, detail="content_type deve ser music, movies ou tv.")
    fid = add_feed_record(url, title=None, content_type=ct)
    if fid <= 0:
        raise HTTPException(status_code=400, detail="Feed já existe ou falha ao adicionar.")
    return {"id": fid}


@router.delete("/{feed_id}")
def remove_feed(feed_id: int) -> dict:
    """Remove um feed por id."""
    deleted = delete_feed_record(feed_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Feed não encontrado.")
    return {"ok": True}


class PollBody(BaseModel):
    format_filter: str | None = None
    include: str | None = None
    exclude: str | None = None


@router.post("/poll")
def poll_feeds(body: PollBody) -> dict:
    """Verifica feeds e salva novidades em pendentes. Deduplica com base em downloads concluídos."""
    existing_names: list[str] = []
    try:
        r = httpx.get(_runner_url("/downloads"), params={"status": "completed"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            for d in data if isinstance(data, list) else []:
                name = d.get("name") or d.get("title") or ""
                if name:
                    existing_names.append(name)
    except Exception as exc:
        logger.debug("Falha ao obter downloads do Runner para dedup: %s", exc)
    result = poll_feeds_api(
        format_filter=body.format_filter,
        include=body.include,
        exclude=body.exclude,
        existing_completed_names=existing_names if existing_names else None,
    )
    saved = result.get("saved") or 0
    if saved > 0:
        try:
            notification_create(
                "feed_verified",
                f"Feeds verificados: {saved} novo(s) item(ns) em pendentes.",
                body=None,
                payload={"saved": saved, "new_count": saved},
            )
        except Exception as exc:
            logger.debug("Falha ao criar notificação de feed: %s", exc)
    return result


@router.get("/pending")
def list_pending() -> list[dict]:
    """Lista itens pendentes (salvos pelo poll)."""
    return pending_list()


class AddToDownloadsBody(BaseModel):
    pending_ids: list[int]
    organize: bool = False


@router.post("/pending/add-to-downloads")
def add_pending_to_downloads(body: AddToDownloadsBody) -> dict:
    """Enfileira itens pendentes no Runner e remove-os da lista pendente."""
    if not body.pending_ids:
        return {"added": [], "errors": ["Nenhum id informado."], "ok": 0, "fail": 0}
    s = get_settings()
    save_path_base = (
        (getattr(s, "download_dir", "") or getattr(s, "watch_folder", "") or "./downloads")
    ).strip()
    save_path_base = str(Path(save_path_base).expanduser().resolve())
    added: list[int] = []
    errors: list[str] = []
    for pid in body.pending_ids:
        it = pending_get(pid)
        if not it:
            errors.append(f"Pendente {pid} não encontrado.")
            continue
        link = it.get("link")
        if not link:
            errors.append(f"[{pid}] Sem link magnet.")
            continue
        title = it.get("title") or ""
        feed = get_feed_by_id(it["feed_id"]) if it.get("feed_id") else None
        content_type = (feed.get("content_type") if feed else None) or "music"
        content_type = str(content_type).strip().lower()
        if content_type not in ("music", "movies", "tv"):
            content_type = "music"
        if body.organize and title:
            subpath = extract_subpath_by_content_type(title, content_type)
            save_path = str(Path(save_path_base) / subpath)
        else:
            save_path = save_path_base
        url = _runner_url("/downloads")
        try:
            resp = httpx.post(
                url,
                json={
                    "magnet": link,
                    "save_path": save_path,
                    "name": title,
                    "content_type": content_type,
                    "start_now": True,
                },
                timeout=30,
            )
        except httpx.HTTPError as e:
            errors.append(f"[{pid}] Runner: {e}")
            continue
        if resp.status_code != 200:
            errors.append(f"[{pid}] {resp.text or resp.status_code}")
            continue
        data = resp.json()
        added.append(data.get("id", 0))
        pending_delete(pid)
    return {"added": added, "errors": errors, "ok": len(added), "fail": len(errors)}
