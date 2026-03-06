"""Rotas de notificações: listar, contagem não lidas, marcar como lida."""

from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ...db import (
    notification_list,
    notification_unread_count,
    notification_mark_read,
    notification_mark_all_read,
    notification_clear_all,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


_KEEPALIVE_INTERVAL = 30.0


async def _stream_notification_events():
    """Generator SSE: envia count de não lidas a cada 10–15 s; keepalive a cada 30s."""
    try:
        last_keepalive = time.monotonic()
        while True:
            count = await asyncio.to_thread(notification_unread_count)
            payload = json.dumps({"count": count})
            yield f"data: {payload}\n\n"
            if time.monotonic() - last_keepalive >= _KEEPALIVE_INTERVAL:
                yield ": keepalive\n\n"
                last_keepalive = time.monotonic()
            await asyncio.sleep(12)
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get("/events")
async def notification_events():
    """SSE: stream de contagem de notificações não lidas (atualização ~12 s)."""
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
    since_id: int | None = Query(None, description="Retornar apenas id < since_id (paginação)"),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
) -> list[dict]:
    """Lista notificações (mais recentes primeiro)."""
    return notification_list(since_id=since_id, limit=limit, unread_only=unread_only)


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
    return {"ok": True}


@router.post("/mark-all-read")
def mark_all_read() -> dict:
    """Marca todas como lidas."""
    count = notification_mark_all_read()
    return {"updated": count}


@router.post("/clear")
def clear_all() -> dict:
    """Remove todas as notificações."""
    count = notification_clear_all()
    return {"deleted": count}
