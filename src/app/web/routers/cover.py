"""Rotas de capa: /api/cover, /api/cover/file/{download_id}."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import FileResponse

from ...deps import get_library_import_repo, get_repo, get_settings
from ..cover_service import fetch_and_cache_cover
from ..cover_service import get_cover_urls

router = APIRouter()


def _fetch_and_cache_import_cover(import_repo, import_id: int, row: dict, size: Literal["small", "large"]) -> Path | None:
    """Busca capa via iTunes/TMDB, salva em covers_path, atualiza o row. Retorna Path ou None."""
    from ...sync_library_imports import _download_cover

    search_term = (row.get("name") or "").strip()
    if not search_term:
        return None
    content_type = (row.get("content_type") or "music").strip() or "music"
    urls = get_cover_urls(content_type, search_term)
    s = get_settings()
    covers_path = s.covers_path
    covers_path.mkdir(parents=True, exist_ok=True)

    small_path_rel: str | None = None
    large_path_rel: str | None = None
    if urls.url_small:
        small_file = covers_path / f"import_{import_id}_small.jpg"
        if _download_cover(urls.url_small, small_file):
            small_path_rel = f"import_{import_id}_small.jpg"
    if urls.url_large and urls.url_large != urls.url_small:
        large_file = covers_path / f"import_{import_id}_large.jpg"
        if _download_cover(urls.url_large, large_file):
            large_path_rel = f"import_{import_id}_large.jpg"
    elif small_path_rel:
        large_path_rel = small_path_rel

    if small_path_rel or large_path_rel:
        import_repo.update_metadata(
            import_id,
            cover_path_small=small_path_rel,
            cover_path_large=large_path_rel,
        )

    chosen = (small_path_rel if size == "small" else large_path_rel) or small_path_rel
    if chosen:
        p = covers_path / chosen
        return p if p.is_file() else None
    return None


def _cover_file_path(download_id: int, size: Literal["small", "large"]) -> Path | None:
    s = get_settings()
    name = f"{download_id}_small.jpg" if size == "small" else f"{download_id}_large.jpg"
    p = s.covers_path / name
    return p if p.is_file() else None


@router.get("/cover/file/{download_id}")
def cover_file(
    download_id: int,
    size: Literal["small", "large"] = Query("small"),
    v: str | None = Query(None, description="Cache-buster (updated_at timestamp)"),
) -> FileResponse:
    """Serve o arquivo de capa em cache. Parâmetro v= permite cache-busting pelo SW."""
    path = _cover_file_path(download_id, size)
    if not path:
        raise HTTPException(status_code=404, detail="Capa não encontrada")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=31536000, immutable"})


def _resolve_import_cover_path(path_str: str) -> Path | None:
    """Resolve path_str para Path. Suporta path absoluto (legado) ou relativo a covers_path."""
    s = get_settings()
    p = (path_str or "").strip()
    if not p:
        return None
    if p.startswith("/"):
        path = Path(p)
    else:
        path = s.covers_path / p
    return path if path.is_file() else None


@router.get("/cover/file/import/{import_id}")
def cover_file_import(
    import_id: int,
    size: Literal["small", "large"] = Query("small"),
    v: str | None = Query(None, description="Cache-buster (updated_at timestamp)"),
) -> FileResponse:
    """Serve a capa de um item importado. Parâmetro v= permite cache-busting pelo SW."""
    import_repo = get_library_import_repo()
    if not import_repo:
        raise HTTPException(status_code=404, detail="Capa não encontrada")
    row = import_repo.get(import_id)
    if not row:
        raise HTTPException(status_code=404, detail="Capa não encontrada")
    path_str = (row.get("cover_path_small") if size == "small" else row.get("cover_path_large")) or row.get("cover_path_small")
    path_str = (path_str or "").strip()

    path = _resolve_import_cover_path(path_str) if path_str else None

    if not path:
        path = _fetch_and_cache_import_cover(import_repo, import_id, row, size)
        if not path:
            raise HTTPException(status_code=404, detail="Capa não encontrada")

    return FileResponse(str(path), media_type="image/jpeg", headers={"Cache-Control": "public, max-age=31536000, immutable"})


@router.get("/cover")
def cover(
    content_type: Literal["music", "movies", "tv"] = Query(...),
    title: str = Query("", description="Nome do item (obrigatório sem download_id/import_id)"),
    download_id: int | None = Query(None, description="ID do download para usar cache ou preencher cache"),
    import_id: int | None = Query(None, description="ID do item importado (library_imports) para capa em disco"),
    size: Literal["small", "large"] = Query("small", description="Tamanho desejado (small/large)"),
) -> dict:
    """URL da capa (iTunes/TMDB). Com download_id ou import_id usa cache em disco."""
    if not (title or title.strip()) and download_id is None and import_id is None:
        raise HTTPException(status_code=400, detail="Informe title, download_id ou import_id.")
    url: str | None = None
    from_cache = False

    if import_id is not None:
        import_repo = get_library_import_repo()
        if import_repo:
            row = import_repo.get(import_id)
            if row:
                path_str = (row.get("cover_path_small") if size == "small" else row.get("cover_path_large")) or row.get("cover_path_small")
                path_resolved = _resolve_import_cover_path(path_str.strip()) if path_str else None
                if path_resolved:
                    ua = row.get("updated_at")
                    v = int(ua.timestamp()) if hasattr(ua, "timestamp") else ""
                    url = f"/api/cover/file/import/{import_id}?size={size}&v={v}"
                    from_cache = True

    if url is None and download_id is not None:
        row = get_repo().get(download_id)
        if row:
            cover_small = (row.get("cover_path_small") or "").strip()
            cover_large = (row.get("cover_path_large") or "").strip()
            path = cover_small if size == "small" else cover_large
            if path and Path(path).is_file():
                ua = row.get("updated_at")
                v = int(ua.timestamp()) if hasattr(ua, "timestamp") else ""
                url = f"/api/cover/file/{download_id}?size={size}&v={v}"
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

    if url is None and import_id is not None:
        import_repo = get_library_import_repo()
        if import_repo:
            row = import_repo.get(import_id)
            name_for_cover = (row.get("name") or title or "").strip() if row else (title or "").strip()
            if name_for_cover:
                urls = get_cover_urls(content_type or "music", name_for_cover)
                url = urls.url_small if size == "small" else urls.url_large

    if url is None:
        urls = get_cover_urls(content_type, title)
        url = urls.url_small if size == "small" else urls.url_large

    return {"url": url, "fromCache": from_cache}
