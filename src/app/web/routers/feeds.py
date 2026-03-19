"""Rotas de Feeds: listar/adicionar/remover feeds, poll, pendentes, adicionar aos downloads."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
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
    """Generator SSE: escuta Redis Pub/Sub para eventos de feeds."""
    from ...event_bus import CHANNEL_FEEDS, async_subscribe
    try:
        async for channel, data in async_subscribe(CHANNEL_FEEDS, keepalive_interval=_KEEPALIVE_INTERVAL):
            if channel:
                yield f"data: {json.dumps({'event': 'feeds_pending_updated'})}\n\n"
            else:
                yield ": keepalive\n\n"
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get("/events")
async def feed_events():
    """SSE: stream de eventos de feeds via Redis Pub/Sub."""
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
def list_feeds(request: Request):
    """Lista todos os feeds (id, url, title, content_type, created_at). ETag para revalidação."""
    data = list_feed_records()
    body = json.dumps(data, default=str, ensure_ascii=False)
    etag = hashlib.md5(body.encode()).hexdigest()
    if request.headers.get("if-none-match") == f'"{etag}"':
        return Response(status_code=304)
    return Response(content=body, media_type="application/json", headers={"ETag": f'"{etag}"', "Cache-Control": "private, max-age=0, must-revalidate"})


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
    from ...event_bus import CHANNEL_FEEDS, publish
    publish(CHANNEL_FEEDS, {"type": "feed_added", "id": fid})
    return {"id": fid}


@router.delete("/{feed_id}")
def remove_feed(feed_id: int) -> dict:
    """Remove um feed por id."""
    deleted = delete_feed_record(feed_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Feed não encontrado.")
    from ...event_bus import CHANNEL_FEEDS, publish
    publish(CHANNEL_FEEDS, {"type": "feed_deleted", "id": feed_id})
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
        from ...event_bus import CHANNEL_FEEDS, publish
        publish(CHANNEL_FEEDS, {"type": "feed_polled", "saved": saved})
    return result


@router.get("/pending")
def list_pending(
    request: Request,
    limit: int | None = Query(None, ge=1, le=500, description="Máximo de itens a retornar"),
    offset: int | None = Query(None, ge=0, description="Pular N itens"),
):
    """Lista itens pendentes (salvos pelo poll). ETag para revalidação."""
    data = pending_list(limit=limit, offset=offset)
    body = json.dumps(data, default=str, ensure_ascii=False)
    etag = hashlib.md5(body.encode()).hexdigest()
    if request.headers.get("if-none-match") == f'"{etag}"':
        return Response(status_code=304)
    return Response(content=body, media_type="application/json", headers={"ETag": f'"{etag}"', "Cache-Control": "private, max-age=0, must-revalidate"})


class AddToDownloadsBody(BaseModel):
    pending_ids: list[int]
    organize: bool = False


@router.post("/pending/add-to-downloads")
def add_pending_to_downloads(body: AddToDownloadsBody) -> dict:
    """Enfileira itens pendentes no Runner e remove-os da lista pendente."""
    if not body.pending_ids:
        return {"added": [], "errors": ["Nenhum id informado."], "ok": 0, "fail": 0}
    s = get_settings()
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
        save_path_base = s.save_path_for_content_type(content_type)
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
    if added:
        from ...event_bus import CHANNEL_FEEDS, publish
        publish(CHANNEL_FEEDS, {"type": "pending_to_downloads", "count": len(added)})
    return {"added": added, "errors": errors, "ok": len(added), "fail": len(errors)}
