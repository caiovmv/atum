"""Rotas de busca: /api/search, /api/search-filter-suggestions, /api/tmdb-detail, /api/add-from-search."""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...deps import get_repo, get_settings
from ...indexer_status import get_enabled_indexers
from ...metadata_from_name import parse_metadata_from_name
from ...quality import parse_quality
from ...search import (
    ALL_INDEXERS,
    DEFAULT_INDEXERS,
    SearchResult,
    get_magnet_for_result,
    result_to_dict,
    search_all,
)
from ..cover_service import get_search_filter_suggestions
from ..cover_service import get_tmdb_detail_by_title

router = APIRouter()

_SEARCH_CACHE: dict[str, tuple[float, list[SearchResult]]] = {}
_SEARCH_CACHE_TTL = 300  # 5 min
_SEARCH_CACHE_MAX = 50


def _cache_key(query: str, limit: int, content_type: str, sort_by: str,
               format_filter: str | None, indexers: list[str]) -> str:
    raw = f"{query}|{limit}|{content_type}|{sort_by}|{format_filter}|{','.join(sorted(indexers))}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_get(key: str) -> list[SearchResult] | None:
    entry = _SEARCH_CACHE.get(key)
    if entry and (time.monotonic() - entry[0]) < _SEARCH_CACHE_TTL:
        return entry[1]
    if entry:
        _SEARCH_CACHE.pop(key, None)
    return None


def _cache_set(key: str, results: list[SearchResult]) -> None:
    if len(_SEARCH_CACHE) >= _SEARCH_CACHE_MAX:
        oldest_key = min(_SEARCH_CACHE, key=lambda k: _SEARCH_CACHE[k][0])
        _SEARCH_CACHE.pop(oldest_key, None)
    _SEARCH_CACHE[key] = (time.monotonic(), results)


def _run_search(
    q: str, limit: int, format_filter: str | None, no_quality_filter: bool,
    music_category_only: bool, content_type: str, indexer_list: list[str],
    sort_by: str,
) -> list[dict]:
    """Executa busca + enriquecimento de metadados (sync, roda em thread). Popula o cache."""
    ck = _cache_key(q, limit, content_type, sort_by, format_filter, indexer_list)
    results = search_all(
        query=q,
        limit=limit,
        format_filter=format_filter or None,
        no_quality_filter=no_quality_filter,
        verbose=False,
        music_category_only=music_category_only,
        content_type=content_type,
        indexers=indexer_list or None,
        sort_by=sort_by,
    )
    _cache_set(ck, results)

    out: list[dict] = []
    for r in results:
        d = result_to_dict(r)
        if not d.get("magnet"):
            resolved = get_magnet_for_result(r)
            if resolved:
                d["magnet"] = resolved
        meta = parse_metadata_from_name(r.title)
        d["parsed_year"] = meta.year
        d["parsed_video_quality"] = meta.video_quality_label
        d["parsed_audio_codec"] = meta.audio_codec
        d["parsed_music_quality"] = meta.music_quality
        d["parsed_cleaned_title"] = meta.cleaned_title or None
        out.append(d)
    return out


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(1000, ge=1, le=1000),
    sort_by: Literal["seeders", "size"] = Query("seeders"),
    content_type: Literal["music", "movies", "tv"] = Query("music"),
    format_filter: str | None = Query(None),
    no_quality_filter: bool = Query(False),
    music_category_only: bool = Query(True),
    indexers: str | None = Query(None, description="Indexadores separados por vírgula (padrão: todos)."),
) -> list[dict]:
    """Busca torrents. Retorna lista com metadados parseados (parsed_year, etc.)."""
    s = get_settings()
    if indexers and indexers.strip():
        indexer_list = [x.strip().lower() for x in indexers.split(",") if x.strip()]
        indexer_list = [x for x in indexer_list if x in ALL_INDEXERS]
    else:
        enabled = get_enabled_indexers(s.redis_url or None)
        indexer_list = [x for x in enabled if x in DEFAULT_INDEXERS]
    if not indexer_list:
        indexer_list = list(DEFAULT_INDEXERS)
    return await asyncio.to_thread(
        _run_search, q, limit, format_filter, no_quality_filter,
        music_category_only, content_type, indexer_list, sort_by,
    )


class ResolveMagnetBody(BaseModel):
    """Corpo para resolver magnet de um resultado (ex.: 1337x que não traz magnet na listagem)."""
    indexer: str
    torrent_id: str


@router.post("/search/resolve-magnet")
async def resolve_magnet(body: ResolveMagnetBody) -> dict:
    """Resolve o magnet para um resultado quando não veio na busca (ex.: 1337x)."""
    indexer = (body.indexer or "").strip().lower()
    torrent_id = (body.torrent_id or "").strip()
    if not indexer or indexer not in ALL_INDEXERS or not torrent_id:
        return {"magnet": None}
    fake = SearchResult(
        title="",
        quality=parse_quality(""),
        seeders=0,
        size="",
        torrent_id=torrent_id,
        indexer=indexer,
        magnet=None,
        torrent_url=None,
    )
    magnet = await asyncio.to_thread(get_magnet_for_result, fake)
    return {"magnet": magnet}


@router.get("/search-filter-suggestions")
async def search_filter_suggestions(
    q: str = Query("", description="Texto da busca para sugerir filtros (TMDB/iTunes)."),
    content_type: Literal["music", "movies", "tv"] = Query("music"),
) -> dict:
    """Sugestões de filtros (anos, gêneros, qualidades) a partir de TMDB ou iTunes."""
    return await asyncio.to_thread(get_search_filter_suggestions, content_type, q or "")


@router.get("/tmdb-detail")
async def tmdb_detail(
    title: str = Query(..., min_length=1),
    content_type: Literal["movies", "tv"] = Query(...),
    year: int | None = Query(None),
) -> dict:
    """Detalhes TMDB (overview, gêneros, runtime, poster, etc.) para filme ou série."""
    detail = await asyncio.to_thread(get_tmdb_detail_by_title, title, content_type, year)
    if not detail:
        raise HTTPException(status_code=404, detail="Nenhum resultado TMDB encontrado.")
    return detail


class AddFromSearchBody(BaseModel):
    query: str
    album: str | None = None
    limit: int = 1000
    sort_by: str = "seeders"
    content_type: str = "music"
    format_filter: str | None = None
    no_quality_filter: bool = False
    music_category_only: bool = True
    indexers: list[str] | None = None
    indices: list[int]
    save_path: str | None = None
    start_now: bool = True


def _runner_url(path: str) -> str:
    base = (get_settings().download_runner_url or "").rstrip("/")
    if not base:
        raise HTTPException(
            status_code=503,
            detail="DOWNLOAD_RUNNER_URL não configurado. Inicie o Runner: dl-torrent runner",
        )
    return f"{base}{path}"


@router.post("/add-from-search")
async def add_from_search(body: AddFromSearchBody) -> dict:
    """Busca (com cache) e resolve magnets dos índices selecionados, enviando ao Runner."""
    full_query = f"{body.query} {body.album or ''}".strip()
    s = get_settings()
    indexer_list = body.indexers
    if not indexer_list:
        enabled = get_enabled_indexers(s.redis_url or None)
        indexer_list = [x for x in enabled if x in DEFAULT_INDEXERS] or list(DEFAULT_INDEXERS)
    else:
        indexer_list = [x.strip().lower() for x in indexer_list if x and x.strip() and x.strip().lower() in ALL_INDEXERS]
        if not indexer_list:
            indexer_list = list(DEFAULT_INDEXERS)

    ck = _cache_key(full_query, body.limit, body.content_type, body.sort_by, body.format_filter, indexer_list)
    results = _cache_get(ck)
    if results is None:
        results = await asyncio.to_thread(
            search_all,
            query=full_query,
            limit=body.limit,
            format_filter=body.format_filter,
            no_quality_filter=body.no_quality_filter,
            verbose=False,
            music_category_only=body.music_category_only,
            content_type=body.content_type,
            indexers=indexer_list,
            sort_by=body.sort_by,
        )
        _cache_set(ck, results)

    save_path = (body.save_path or "").strip() or s.save_path_for_content_type(body.content_type)
    added: list[int] = []
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for i in body.indices:
            if i < 0 or i >= len(results):
                errors.append(f"Índice {i} fora do intervalo.")
                continue
            result = results[i]
            magnet = get_magnet_for_result(result)
            if not magnet:
                errors.append(f"Sem magnet: {result.title[:50]}…")
                continue
            url = _runner_url("/downloads")
            try:
                resp = await client.post(
                    url,
                    json={
                        "magnet": magnet,
                        "save_path": save_path,
                        "name": result.title,
                        "content_type": body.content_type,
                        "start_now": body.start_now,
                    },
                )
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"Runner: {e}") from e
            if resp.status_code != 200:
                errors.append(resp.text or f"HTTP {resp.status_code}")
                continue
            data = resp.json()
            added.append(data.get("id", 0))
    return {"added": added, "errors": errors, "ok": len(added), "fail": len(errors)}
