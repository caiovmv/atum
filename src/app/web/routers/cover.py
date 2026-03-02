"""Rotas de capa: /api/cover, /api/cover/file/{download_id}."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import FileResponse

from ...deps import get_repo, get_settings
from ..cover_service import fetch_and_cache_cover
from ..cover_service import get_cover_urls

router = APIRouter()


def _cover_file_path(download_id: int, size: Literal["small", "large"]) -> Path | None:
    s = get_settings()
    name = f"{download_id}_small.jpg" if size == "small" else f"{download_id}_large.jpg"
    p = s.covers_path / name
    return p if p.is_file() else None


@router.get("/cover/file/{download_id}")
def cover_file(
    download_id: int,
    size: Literal["small", "large"] = Query("small"),
) -> FileResponse:
    """Serve o arquivo de capa em cache (pequeno ou grande)."""
    path = _cover_file_path(download_id, size)
    if not path:
        raise HTTPException(status_code=404, detail="Capa não encontrada")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/cover")
def cover(
    content_type: Literal["music", "movies", "tv"] = Query(...),
    title: str = Query("", description="Nome do item (obrigatório sem download_id)"),
    download_id: int | None = Query(None, description="ID do download para usar cache ou preencher cache"),
    size: Literal["small", "large"] = Query("small", description="Tamanho desejado (small/large)"),
) -> dict:
    """URL da capa (iTunes/TMDB). Com download_id usa/salva cache em disco."""
    if not (title or title.strip()) and download_id is None:
        raise HTTPException(status_code=400, detail="Informe title ou download_id.")
    url: str | None = None
    from_cache = False

    if download_id is not None:
        row = get_repo().get(download_id)
        if row:
            cover_small = (row.get("cover_path_small") or "").strip()
            cover_large = (row.get("cover_path_large") or "").strip()
            path = cover_small if size == "small" else cover_large
            if path and Path(path).is_file():
                url = f"/api/cover/file/{download_id}?size={size}"
                from_cache = True
            if not from_cache and (row.get("name") or "").strip():
                urls = fetch_and_cache_cover(download_id, content_type or "music", row.get("name") or title)
                path_after = _cover_file_path(download_id, size)
                if path_after:
                    url = f"/api/cover/file/{download_id}?size={size}"
                    from_cache = True
                else:
                    chosen = urls.url_small if size == "small" else urls.url_large
                    if chosen:
                        url = chosen

    if url is None:
        urls = get_cover_urls(content_type, title)
        url = urls.url_small if size == "small" else urls.url_large

    return {"url": url, "fromCache": from_cache}
