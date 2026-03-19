"""Status dos indexadores (ok/fail) em Redis. Usado pela busca e pelo indexers-daemon."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .indexers import ALL_INDEXERS, INDEXER_BASE_URL_ATTR

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "dl-torrent:indexer:status:"

_cached_client = None
_cached_client_url: str | None = None


def get_indexer_base_urls(settings: "Settings") -> dict[str, str]:
    """Retorna { indexer: base_url } apenas para indexadores com URL não vazia."""
    out: dict[str, str] = {}
    for name in ALL_INDEXERS:
        attr = INDEXER_BASE_URL_ATTR.get(name)
        if not attr:
            continue
        url = (getattr(settings, attr, None) or "").strip().rstrip("/")
        if url:
            out[name] = url
    return out


def _redis_client(redis_url: str):
    global _cached_client, _cached_client_url
    if _cached_client is not None and _cached_client_url == redis_url:
        try:
            _cached_client.ping()
            return _cached_client
        except Exception:
            _cached_client = None
    import redis
    _cached_client = redis.from_url(redis_url, decode_responses=True)
    _cached_client_url = redis_url
    return _cached_client


def get_indexer_status(redis_url: str | None) -> dict[str, bool]:
    """
    Retorna status de cada indexador: { "1337x": True, "tpb": False, ... }.
    Ausência de chave ou Redis indisponível → considerado ok (True).
    Uses mget for a single round-trip.
    """
    names = sorted(ALL_INDEXERS)
    if not (redis_url or "").strip():
        return {name: True for name in names}
    try:
        client = _redis_client(redis_url.strip())
        keys = [REDIS_KEY_PREFIX + name for name in names]
        values = client.mget(keys)
        return {name: val != "fail" for name, val in zip(names, values)}
    except Exception as e:
        logger.warning("indexer_status get_indexer_status failed: %s", e)
        return {name: True for name in names}


def get_enabled_indexers(redis_url: str | None) -> list[str]:
    """
    Retorna lista de indexadores com status ok (habilitados para busca).
    Se Redis indisponível ou sem chave, retorna todos (DEFAULT_INDEXERS não é usado aqui;
    quem chama pode intersectar com DEFAULT_INDEXERS se quiser).
    """
    status = get_indexer_status(redis_url)
    return [name for name in sorted(ALL_INDEXERS) if status.get(name, True)]


_STATUS_TTL_SECONDS = 300


def set_indexer_status(redis_url: str | None, indexer: str, ok: bool) -> None:
    """Escreve status do indexador no Redis com TTL de 5 min."""
    if not (redis_url or "").strip():
        return
    if indexer not in ALL_INDEXERS:
        return
    try:
        client = _redis_client(redis_url.strip())
        key = REDIS_KEY_PREFIX + indexer
        client.setex(key, _STATUS_TTL_SECONDS, "ok" if ok else "fail")
    except Exception as e:
        logger.warning("indexer_status set_indexer_status failed: %s", e)


def run_health_cycle(
    settings: "Settings",
    redis_url: str | None,
    probe_timeout_sec: int = 10,
    retry_delay_sec: float = 2.0,
) -> dict[str, bool]:
    """
    Executa um ciclo de health-check em paralelo usando probe de busca.
    Para cada indexador com base_url configurada, chama probe_indexer; em falha, faz
    uma nova tentativa após retry_delay_sec. Grava resultado no Redis e retorna { indexer: ok }.
    """
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from .search import probe_indexer

    base_urls = get_indexer_base_urls(settings)
    if not base_urls:
        return {}

    def _probe_one(name: str) -> tuple[str, bool]:
        try:
            ok = probe_indexer(name, settings=settings, timeout_sec=probe_timeout_sec)
            if not ok and retry_delay_sec > 0:
                time.sleep(retry_delay_sec)
                ok = probe_indexer(name, settings=settings, timeout_sec=probe_timeout_sec)
        except Exception as e:
            logger.warning("indexer_status run_health_cycle probe %s: %s", name, e)
            ok = False
        return name, ok

    result: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=min(len(base_urls), 6)) as pool:
        futures = {pool.submit(_probe_one, n): n for n in sorted(base_urls.keys())}
        for future in as_completed(futures):
            name, ok = future.result()
            result[name] = ok
            logger.info("indexer check %s: %s", name, "ok" if ok else "fail")

    if result and redis_url and (redis_url or "").strip():
        try:
            client = _redis_client(redis_url.strip())
            pipe = client.pipeline(transaction=False)
            for name, ok in result.items():
                pipe.setex(REDIS_KEY_PREFIX + name, _STATUS_TTL_SECONDS, "ok" if ok else "fail")
            pipe.execute()
        except Exception as e:
            logger.warning("indexer_status run_health_cycle redis pipeline failed: %s", e)
        try:
            from .event_bus import CHANNEL_INDEXERS, publish
            publish(CHANNEL_INDEXERS, result)
        except Exception as e:
            logger.debug("indexer_status publish failed: %s", e)

    return result
