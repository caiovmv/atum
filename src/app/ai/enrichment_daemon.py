"""Lógica do ciclo do daemon de enriquecimento."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_ENRICHMENT_MAX_WORKERS = int(os.environ.get("ENRICHMENT_MAX_WORKERS", "5"))


def _get_settings_value(key: str, default: Any = None) -> Any:
    """Obtém valor de uma setting (runtime DB > default)."""
    from ..deps import get_settings_repo
    repo = get_settings_repo()
    if repo:
        v = repo.get(key)
        if v is not None:
            return v
    return default


def _settings_bool(key: str, default: bool = False) -> bool:
    """Obtém setting como bool (trata strings 'false'/'0'/'' como False)."""
    v = _get_settings_value(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() not in ("", "0", "false", "no")
    return bool(v)


def _enrich_single(item: dict, llm_client: Any, repo: Any) -> dict:
    """Enriquece um único item (thread-safe). Retorna update_data ou levanta exceção."""
    ct = (item.get("content_type") or "music").strip().lower()
    if ct == "movie":
        ct = "movies"

    if ct == "music":
        from .enrich_music import enrich_music_item
        result = enrich_music_item(item, llm_client=llm_client)
    else:
        from .enrich_video import enrich_video_item
        result = enrich_video_item(item)

    return result.to_update_dict()


def run_enrichment_cycle(batch_size: int = 10) -> int:
    """Um ciclo: busca itens pendentes (imports + downloads), enriquece em paralelo, salva. Retorna qtd processada."""
    from ..deps import get_library_import_repo, get_llm_client

    llm_client = None
    if _settings_bool("enrichment_enabled"):
        llm_client = get_llm_client()

    repo = get_library_import_repo()
    if not repo:
        logger.warning("Library import repo não disponível")
        return _enrich_downloads_cycle(batch_size, llm_client)

    retry_hours = int(_get_settings_value("enrichment_retry_after_hours", 0) or 0)
    items = repo.list_pending_enrichment(limit=batch_size, retry_after_hours=retry_hours)
    if not items:
        return _enrich_downloads_cycle(batch_size, llm_client)

    processed = 0
    max_workers = min(len(items), _ENRICHMENT_MAX_WORKERS)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_item = {
            pool.submit(_enrich_single, item, llm_client, repo): item
            for item in items
        }
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                update_data = future.result()
                repo.update_metadata(item["id"], **update_data)
                processed += 1
                logger.info(
                    "Enriched: %s (%s) - sources: %s",
                    item.get("name", "?"),
                    (item.get("content_type") or "music").strip().lower(),
                    update_data.get("enrichment_sources", []),
                )
            except Exception as e:
                logger.warning(
                    "Enrichment error for %s (id=%s): %s",
                    item.get("name", "?"), item.get("id"), e,
                )
                try:
                    repo.update_metadata(
                        item["id"],
                        enrichment_error=str(e)[:500],
                        enriched_at=datetime.now(timezone.utc).isoformat(),
                    )
                except Exception:
                    pass

    if processed > 0:
        try:
            from ..db import notification_create
            notification_create(
                "enrichment_done",
                f"Enriquecimento: {processed} itens processados",
                payload={"processed": processed, "batch_size": batch_size},
            )
        except Exception as exc:
            logger.debug("Falha ao criar notificação de enrichment: %s", exc)
        try:
            from ..event_bus import CACHE_FACETS_PREFIX, CHANNEL_LIBRARY, cache_delete_pattern, publish
            enriched_ids = [item.get("id") for item in items if item.get("id")]
            publish(CHANNEL_LIBRARY, {
                "type": "enrichment_completed",
                "ids": enriched_ids[:50],
                "facets_dirty": True,
                "covers_dirty": enriched_ids[:50],
            })
            cache_delete_pattern(f"{CACHE_FACETS_PREFIX}:*")
        except Exception as exc:
            logger.debug("Falha ao publicar evento de enrichment: %s", exc)

    dl_processed = _enrich_downloads_cycle(batch_size, llm_client)

    return processed + dl_processed


def _enrich_downloads_cycle(batch_size: int, llm_client: Any) -> int:
    """Enriquece downloads completed que ainda não foram processados pelo enrichment."""
    from ..deps import get_repo

    repo = get_repo()
    if not repo or not hasattr(repo, "list_pending_enrichment"):
        return 0

    items = repo.list_pending_enrichment(limit=batch_size)
    if not items:
        return 0

    processed = 0
    max_workers = min(len(items), _ENRICHMENT_MAX_WORKERS)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_item = {
            pool.submit(_enrich_single, item, llm_client, repo): item
            for item in items
        }
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                update_data = future.result()
                if hasattr(repo, "update_full_enrichment"):
                    repo.update_full_enrichment(item["id"], **update_data)
                else:
                    safe = {k: v for k, v in update_data.items()
                            if k in ("artist", "album", "genre", "tmdb_id", "imdb_id", "content_type")}
                    if safe:
                        repo.update_enrichment(item["id"], **safe)
                processed += 1
                logger.info(
                    "Enriched download: %s (id=%s) - sources: %s",
                    item.get("name", "?"), item.get("id"),
                    update_data.get("enrichment_sources", []),
                )
            except Exception as e:
                logger.warning(
                    "Download enrichment error for %s (id=%s): %s",
                    item.get("name", "?"), item.get("id"), e,
                )
                try:
                    if hasattr(repo, "update_full_enrichment"):
                        repo.update_full_enrichment(
                            item["id"],
                            enrichment_error=str(e)[:500],
                            enriched_at=datetime.now(timezone.utc).isoformat(),
                        )
                except Exception:
                    pass

    if processed > 0:
        try:
            from ..event_bus import CACHE_FACETS_PREFIX, CHANNEL_LIBRARY, cache_delete_pattern, publish
            publish(CHANNEL_LIBRARY, {
                "type": "download_enrichment_completed",
                "count": processed,
                "facets_dirty": True,
            })
            cache_delete_pattern(f"{CACHE_FACETS_PREFIX}:*")
        except Exception:
            pass

    return processed
