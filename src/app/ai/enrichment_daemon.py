"""Lógica do ciclo do daemon de enriquecimento."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_ENRICHMENT_MAX_WORKERS = 3


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
    """Um ciclo: busca itens pendentes, enriquece em paralelo, salva. Retorna qtd processada."""
    from ..deps import get_library_import_repo, get_llm_client

    repo = get_library_import_repo()
    if not repo:
        logger.warning("Library import repo não disponível")
        return 0

    retry_hours = int(_get_settings_value("enrichment_retry_after_hours", 0) or 0)
    items = repo.list_pending_enrichment(limit=batch_size, retry_after_hours=retry_hours)
    if not items:
        return 0

    llm_client = None
    if _settings_bool("enrichment_enabled"):
        llm_client = get_llm_client()

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

    return processed
