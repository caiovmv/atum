"""Rotas de notificações: listar, contagem não lidas, marcar como lida."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from ...db import (
    notification_list,
    notification_unread_count,
    notification_mark_read,
    notification_mark_all_read,
    notification_clear_all,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


_KEEPALIVE_INTERVAL = 30.0


async def _stream_notification_events():
    """Generator SSE: escuta Redis Pub/Sub para notificações em tempo real."""
    from ...event_bus import CHANNEL_NOTIFICATIONS, async_subscribe

    count = await asyncio.to_thread(notification_unread_count)
    yield f"data: {json.dumps({'count': count})}\n\n"

    try:
        async for channel, data in async_subscribe(CHANNEL_NOTIFICATIONS, keepalive_interval=_KEEPALIVE_INTERVAL):
            if channel:
                try:
                    count = await asyncio.to_thread(notification_unread_count)
                except Exception:
                    count = 0
                notif = data.get("notification")
                if notif:
                    payload = json.dumps({"count": count, "notification": notif})
                    yield f"event: new_notification\ndata: {payload}\n\n"
                else:
                    yield f"data: {json.dumps({'count': count})}\n\n"
            else:
                yield ": keepalive\n\n"
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get("/events")
async def notification_events():
    """SSE: stream de notificações via Redis Pub/Sub."""
    return StreamingResponse(
        _stream_notification_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("")
def list_notifications(
    request: Request,
    since_id: int | None = Query(None, description="Retornar apenas id < since_id (paginação)"),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
):
    """Lista notificações (mais recentes primeiro). ETag para revalidação."""
    data = notification_list(since_id=since_id, limit=limit, unread_only=unread_only)
    body = json.dumps(data, default=str, ensure_ascii=False)
    etag = hashlib.md5(body.encode()).hexdigest()
    if request.headers.get("if-none-match") == f'"{etag}"':
        return Response(status_code=304)
    return Response(content=body, media_type="application/json", headers={"ETag": f'"{etag}"', "Cache-Control": "private, max-age=0, must-revalidate"})


@router.get("/unread-count")
def unread_count() -> dict:
    """Retorna a quantidade de notificações não lidas."""
    return {"count": notification_unread_count()}


@router.patch("/{notification_id}/read")
def mark_read(notification_id: int) -> dict:
    """Marca uma notificação como lida."""
    ok = notification_mark_read(notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    from ...event_bus import CHANNEL_NOTIFICATIONS, publish
    publish(CHANNEL_NOTIFICATIONS, {"type": "read", "id": notification_id})
    return {"ok": True}


@router.post("/mark-all-read")
def mark_all_read() -> dict:
    """Marca todas como lidas."""
    count = notification_mark_all_read()
    from ...event_bus import CHANNEL_NOTIFICATIONS, publish
    publish(CHANNEL_NOTIFICATIONS, {"type": "mark_all_read", "updated": count})
    return {"updated": count}


@router.post("/clear")
def clear_all() -> dict:
    """Remove todas as notificações."""
    count = notification_clear_all()
    from ...event_bus import CHANNEL_NOTIFICATIONS, publish
    publish(CHANNEL_NOTIFICATIONS, {"type": "cleared", "deleted": count})
    return {"deleted": count}
