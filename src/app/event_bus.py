"""Event bus centralizado via Redis Pub/Sub para propagação de eventos entre serviços.

Substitui polling no banco por notificação instantânea entre containers
(api, runner, sync-daemon, enrichment-daemon).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)

CHANNEL_LIBRARY = "dl-torrent:events:library"
CHANNEL_DOWNLOADS = "dl-torrent:events:downloads"
CHANNEL_NOTIFICATIONS = "dl-torrent:events:notifications"
CHANNEL_FEEDS = "dl-torrent:events:feeds"
CHANNEL_WISHLIST = "dl-torrent:events:wishlist"
CHANNEL_INDEXERS = "dl-torrent:events:indexers"
CHANNEL_SETTINGS = "dl-torrent:events:settings"

CACHE_FACETS_PREFIX = "dl-torrent:cache:facets"
CACHE_SETTINGS_PREFIX = "dl-torrent:cache:settings"

_INDEXER_STATUS_TTL = 300  # 5 min

_sync_client = None


def _get_redis_url() -> str:
    try:
        from .deps import get_settings
        return (get_settings().redis_url or "").strip()
    except Exception:
        return ""


def _get_sync_client():
    global _sync_client
    redis_url = _get_redis_url()
    if not redis_url:
        return None
    if _sync_client is None:
        import redis
        _sync_client = redis.from_url(redis_url, decode_responses=True)
    return _sync_client


# ---------------------------------------------------------------------------
# Publish (sync — used by daemons, workers, API handlers)
# ---------------------------------------------------------------------------

def publish(channel: str, data: dict[str, Any] | None = None) -> None:
    """Publica evento no canal Redis. No-op se Redis não configurado."""
    client = _get_sync_client()
    if not client:
        return
    try:
        client.publish(channel, json.dumps(data or {}))
    except Exception as e:
        logger.debug("event_bus publish error (%s): %s", channel, e)


# ---------------------------------------------------------------------------
# Subscribe (async — used by SSE endpoints)
# ---------------------------------------------------------------------------

async def async_subscribe(
    *channels: str,
    keepalive_interval: float = 30.0,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Async generator que escuta canais Redis via Pub/Sub.

    Yields (channel, data) para cada mensagem recebida.
    Yield ("", {}) a cada keepalive_interval se sem mensagens (para keepalive SSE).
    Se Redis não disponível, faz fallback para keepalive-only.
    """
    redis_url = _get_redis_url()
    if not redis_url:
        while True:
            await asyncio.sleep(keepalive_interval)
            yield ("", {})
        return  # pragma: no cover

    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(*channels)
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=keepalive_interval),
                        timeout=keepalive_interval + 5,
                    )
                except asyncio.TimeoutError:
                    msg = None
                if msg and msg.get("type") == "message":
                    try:
                        data = json.loads(msg["data"])
                    except (json.JSONDecodeError, TypeError):
                        data = {}
                    yield (msg.get("channel", ""), data)
                else:
                    yield ("", {})
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.aclose()
            await client.aclose()
    except Exception as e:
        logger.warning("event_bus async_subscribe error: %s — falling back to keepalive", e)
        while True:
            await asyncio.sleep(keepalive_interval)
            yield ("", {})


# ---------------------------------------------------------------------------
# Cache helpers (Redis key-value com TTL)
# ---------------------------------------------------------------------------

def cache_get(key: str) -> dict[str, Any] | list | None:
    client = _get_sync_client()
    if not client:
        return None
    try:
        data = client.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    client = _get_sync_client()
    if not client:
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        pass


def cache_delete(key: str) -> None:
    client = _get_sync_client()
    if not client:
        return
    try:
        client.delete(key)
    except Exception:
        pass


def cache_delete_pattern(pattern: str) -> None:
    client = _get_sync_client()
    if not client:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor, match=pattern, count=100)
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass
