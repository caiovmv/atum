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
    """Generator SSE: envia status dos indexadores a cada 60 s; keepalive a cada 30s."""
    try:
        while True:
            s = get_settings()
            status = await asyncio.to_thread(get_indexer_status, s.redis_url or None)
            yield f"data: {json.dumps(status)}\n\n"
            await asyncio.sleep(_KEEPALIVE_INTERVAL)
            yield ": keepalive\n\n"
            await asyncio.sleep(_KEEPALIVE_INTERVAL)
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get("/events")
async def indexers_events():
    """SSE: stream de status dos indexadores (atualização a cada 60 s)."""
    return StreamingResponse(
        _stream_indexer_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
