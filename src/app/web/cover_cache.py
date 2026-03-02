"""Cache de capas: apenas Redis (DIP). Sem REDIS_URL não cacheia (no-op). Prefixo dl-torrent:."""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)

PREFIX = "dl-torrent:cover:"
SEARCH_PREFIX = "dl-torrent:search:"
# Download: eviction controla; TTL só failsafe
COVER_DOWNLOAD_TTL_SECONDS = 7 * 24 * 3600  # 7 dias
# Pesquisa: só TTL, máx 1 dia
COVER_SEARCH_TTL_SECONDS = 24 * 3600  # 1 dia


class CoverCache(Protocol):
    """Abstração de cache para capas. Suporta eviction por download_id."""

    def get(self, key: str) -> dict[str, Any] | None:
        ...

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int = COVER_SEARCH_TTL_SECONDS) -> None:
        ...

    def evict(self, key: str) -> None:
        """Remove uma chave do cache."""
        ...

    def evict_download(self, download_id: int) -> None:
        """Remove cache da capa associada ao download_id."""
        ...


def _cache_key(content_type: str, title: str) -> str:
    t = (title or "").strip().lower()[:200]
    return f"{PREFIX}title:{content_type}:{t}"


def download_cache_key(download_id: int) -> str:
    return f"{PREFIX}download:{download_id}"


class NoOpCoverCache:
    """Cache que não armazena nada (quando REDIS_URL não está definido)."""

    def get(self, key: str) -> dict[str, Any] | None:
        return None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int = COVER_SEARCH_TTL_SECONDS) -> None:
        pass

    def evict(self, key: str) -> None:
        pass

    def evict_download(self, download_id: int) -> None:
        pass


class RedisCoverCache:
    """Cache em Redis. Prefixo dl-torrent:."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redis
            self._client = redis.from_url(self._redis_url, decode_responses=True)
        return self._client

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            data = self._get_client().get(key)
            if not data:
                return None
            return json.loads(data)
        except Exception as e:
            logger.warning("Redis cover cache get failed: %s", e)
            return None

    def set(self, key: str, value: dict[str, Any], ttl_seconds: int = COVER_SEARCH_TTL_SECONDS) -> None:
        try:
            self._get_client().setex(key, ttl_seconds, json.dumps(value))
        except Exception as e:
            logger.warning("Redis cover cache set failed: %s", e)

    def evict(self, key: str) -> None:
        try:
            self._get_client().delete(key)
        except Exception as e:
            logger.warning("Redis cover cache evict failed: %s", e)

    def evict_download(self, download_id: int) -> None:
        self.evict(download_cache_key(download_id))


_cover_cache: CoverCache | None = None


def get_cover_cache() -> CoverCache:
    """Retorna o cache de capas (apenas Redis). Sem REDIS_URL retorna no-op (não cacheia)."""
    global _cover_cache
    if _cover_cache is not None:
        return _cover_cache
    from ..deps import get_settings
    redis_url = (get_settings().redis_url or "").strip()
    if redis_url:
        _cover_cache = RedisCoverCache(redis_url)
    else:
        _cover_cache = NoOpCoverCache()
    return _cover_cache


def set_cover_cache(cache: CoverCache | None) -> None:
    """Injeta o cache (para testes). None restaura o padrão."""
    global _cover_cache
    _cover_cache = cache
