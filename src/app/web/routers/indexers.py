"""Rotas de status dos indexadores (para filtros e busca)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...deps import get_settings
from ...indexer_status import get_indexer_status

router = APIRouter(prefix="/indexers", tags=["indexers"])


@router.get("/status")
def indexers_status() -> dict[str, bool]:
    """Retorna status de cada indexador (true = habilitado, false = desativado). Baseado no último probe de busca (mesmo código que a busca)."""
    s = get_settings()
    return get_indexer_status(s.redis_url or None)


_KEEPALIVE_INTERVAL = 30.0


async def _stream_indexer_events():
    """Generator SSE: escuta Redis Pub/Sub para status dos indexadores."""
    from ...event_bus import CHANNEL_INDEXERS, async_subscribe

    s = get_settings()
    status = await asyncio.to_thread(get_indexer_status, s.redis_url or None)
    yield f"data: {json.dumps(status)}\n\n"

    try:
        async for channel, data in async_subscribe(CHANNEL_INDEXERS, keepalive_interval=_KEEPALIVE_INTERVAL):
            if channel and data:
                yield f"data: {json.dumps(data)}\n\n"
            else:
                yield ": keepalive\n\n"
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get("/events")
async def indexers_events():
    """SSE: stream de status dos indexadores via Redis Pub/Sub."""
    return StreamingResponse(
        _stream_indexer_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
