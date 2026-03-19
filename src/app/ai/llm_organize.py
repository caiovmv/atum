"""AI-powered organization: LLM fallback para parsing, correção de metadados e auto-detect content_type."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {}
_CACHE_MAX = 500


def _cache_get(key: str) -> Any | None:
    return _CACHE.get(key)


def _cache_set(key: str, value: Any) -> None:
    if len(_CACHE) >= _CACHE_MAX:
        oldest = next(iter(_CACHE))
        del _CACHE[oldest]
    _CACHE[key] = value


def _get_client():
    from .llm_client import LLMClient
    return LLMClient.from_settings()


def _get_repo():
    from ..deps import get_settings_repo
    repo = get_settings_repo()
    return repo if repo is not None else {"ai_prompts": {}}


def llm_parse_torrent_name(torrent_name: str) -> dict | None:
    """Usa LLM para extrair artist, album, year, show, season, episode, content_type de um nome de torrent.
    Retorna dict com campos extraídos ou None se falhar."""
    cache_key = f"parse:{torrent_name}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    client = _get_client()
    if not client:
        return None

    from .prompts_registry import get_prompt_config
    repo = _get_repo()
    config = get_prompt_config("parse_torrent", repo)
    try:
        result = client.chat_json([
            {"role": "system", "content": config["system"]},
            {"role": "user", "content": torrent_name},
        ], temperature=config["temperature"])

        if result and isinstance(result, dict) and any(k in result for k in ("title", "artist", "content_type")):
            _cache_set(cache_key, result)
            logger.info("LLM parsed torrent name: %s -> %s", torrent_name[:60], result)
            return result
    except Exception as e:
        logger.debug("LLM parse_torrent_name failed: %s", e)

    return None


def llm_fix_audio_metadata(
    filename: str,
    existing_artist: str | None = None,
    existing_album: str | None = None,
    existing_title: str | None = None,
    existing_year: int | None = None,
    existing_genre: str | None = None,
    folder_path: str | None = None,
) -> dict | None:
    """Usa LLM para corrigir/preencher metadados de áudio incompletos.
    Retorna dict com campos corrigidos ou None se falhar."""
    cache_key = f"fix_meta:{filename}:{existing_artist}:{existing_album}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    has_artist = bool(existing_artist and existing_artist.strip())
    has_album = bool(existing_album and existing_album.strip())
    has_title = bool(existing_title and existing_title.strip())
    if has_artist and has_album and has_title:
        return None

    client = _get_client()
    if not client:
        return None

    existing = {}
    if existing_artist:
        existing["artist"] = existing_artist
    if existing_album:
        existing["album"] = existing_album
    if existing_title:
        existing["title"] = existing_title
    if existing_year:
        existing["year"] = existing_year
    if existing_genre:
        existing["genre"] = existing_genre

    context_parts = [f"Filename: {filename}"]
    if folder_path:
        context_parts.append(f"Folder path: {folder_path}")
    if existing:
        context_parts.append(f"Existing tags: {json.dumps(existing)}")

    from .prompts_registry import get_prompt_config
    repo = _get_repo()
    config = get_prompt_config("fix_metadata", repo)
    try:
        result = client.chat_json([
            {"role": "system", "content": config["system"]},
            {"role": "user", "content": "\n".join(context_parts)},
        ], temperature=config["temperature"])

        if result and isinstance(result, dict):
            merged = {**existing}
            for k in ("artist", "album", "title", "year", "genre"):
                if k in result and result[k] and not existing.get(k):
                    merged[k] = result[k]
            _cache_set(cache_key, merged)
            logger.info("LLM fixed metadata for %s: %s", filename[:60], merged)
            return merged
    except Exception as e:
        logger.debug("LLM fix_audio_metadata failed: %s", e)

    return None


def llm_detect_content_type(name: str) -> tuple[str, float] | None:
    """Usa LLM para determinar content_type quando heurísticas são incertas.
    Retorna (content_type, confidence) ou None se falhar.
    confidence é 0.0-1.0."""
    cache_key = f"detect_ct:{name}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    client = _get_client()
    if not client:
        return None

    from .prompts_registry import get_prompt_config
    repo = _get_repo()
    config = get_prompt_config("detect_content_type", repo)
    try:
        result = client.chat_json([
            {"role": "system", "content": config["system"]},
            {"role": "user", "content": name},
        ], temperature=config["temperature"])

        if result and "content_type" in result:
            ct = result["content_type"]
            conf = float(result.get("confidence", 0.5))
            if ct in ("music", "movies", "tv"):
                out = (ct, conf)
                _cache_set(cache_key, out)
                logger.info("LLM detected content_type for %s: %s (%.0f%%)", name[:60], ct, conf * 100)
                return out
    except Exception as e:
        logger.debug("LLM detect_content_type failed: %s", e)

    return None
