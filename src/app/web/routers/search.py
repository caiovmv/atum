"""Rotas de busca: /api/search, /api/search-filter-suggestions, /api/tmdb-detail, /api/add-from-search."""

from __future__ import annotations

from typing import Literal

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...deps import get_repo, get_settings
from ...metadata_from_name import parse_metadata_from_name
from ...search import (
    get_magnet_for_result,
    result_to_dict,
    search_all,
)
from ..cover_service import get_search_filter_suggestions
from ..cover_service import get_tmdb_detail_by_title

router = APIRouter()


@router.get("/search")
def search(
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
    from ...search import ALL_INDEXERS, DEFAULT_INDEXERS
    indexer_list = [x.strip().lower() for x in (indexers or ",".join(DEFAULT_INDEXERS)).split(",") if x.strip()]
    indexer_list = [x for x in indexer_list if x in ALL_INDEXERS]
    if not indexer_list:
        indexer_list = list(DEFAULT_INDEXERS)
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
    out: list[dict] = []
    for r in results:
        d = result_to_dict(r)
        meta = parse_metadata_from_name(r.title)
        d["parsed_year"] = meta.year
        d["parsed_video_quality"] = meta.video_quality_label
        d["parsed_audio_codec"] = meta.audio_codec
        d["parsed_music_quality"] = meta.music_quality
        d["parsed_cleaned_title"] = meta.cleaned_title or None
        out.append(d)
    return out


@router.get("/search-filter-suggestions")
def search_filter_suggestions(
    q: str = Query("", description="Texto da busca para sugerir filtros (TMDB/iTunes)."),
    content_type: Literal["music", "movies", "tv"] = Query("music"),
) -> dict:
    """Sugestões de filtros (anos, gêneros, qualidades) a partir de TMDB ou iTunes."""
    return get_search_filter_suggestions(content_type, q or "")


@router.get("/tmdb-detail")
def tmdb_detail(
    title: str = Query(..., min_length=1),
    content_type: Literal["movies", "tv"] = Query(...),
    year: int | None = Query(None),
) -> dict:
    """Detalhes TMDB (overview, gêneros, runtime, poster, etc.) para filme ou série."""
    detail = get_tmdb_detail_by_title(title, content_type, year)
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
def add_from_search(body: AddFromSearchBody) -> dict:
    """Reexecuta a busca, resolve magnets dos índices e envia ao Runner."""
    full_query = f"{body.query} {body.album or ''}".strip()
    results = search_all(
        query=full_query,
        limit=body.limit,
        format_filter=body.format_filter,
        no_quality_filter=body.no_quality_filter,
        verbose=False,
        music_category_only=body.music_category_only,
        content_type=body.content_type,
        indexers=body.indexers,
        sort_by=body.sort_by,
    )
    s = get_settings()
    save_path = (
        (body.save_path or "").strip()
        or getattr(s, "download_dir", "")
        or getattr(s, "watch_folder", "")
        or "./downloads"
    )
    added: list[int] = []
    errors: list[str] = []
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
            resp = requests.post(
                url,
                json={
                    "magnet": magnet,
                    "save_path": save_path,
                    "name": result.title,
                    "content_type": body.content_type,
                    "start_now": body.start_now,
                },
                timeout=30,
            )
        except requests.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Runner: {e}") from e
        if resp.status_code != 200:
            errors.append(resp.text or f"HTTP {resp.status_code}")
            continue
        data = resp.json()
        added.append(data.get("id", 0))
    return {"added": added, "errors": errors, "ok": len(added), "fail": len(errors)}
