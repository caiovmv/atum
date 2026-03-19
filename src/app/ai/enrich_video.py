"""Pipeline de enriquecimento de vídeo: TMDB completo para library_imports."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class VideoEnrichmentResult:
    """Resultado do enriquecimento de vídeo via TMDB."""
    tmdb_id: int | None = None
    imdb_id: str | None = None
    overview: str | None = None
    original_title: str | None = None
    vote_average: float | None = None
    runtime_minutes: int | None = None
    tmdb_genres: list[str] = field(default_factory=list)
    backdrop_path: str | None = None
    name: str | None = None
    year: int | None = None
    cover_path_small: str | None = None
    cover_path_large: str | None = None
    enrichment_sources: list[str] = field(default_factory=list)
    enriched_at: str | None = None

    def to_update_dict(self) -> dict:
        """Retorna dict com apenas campos não-None para update_metadata."""
        d: dict = {}
        if self.tmdb_id is not None:
            d["tmdb_id"] = self.tmdb_id
        if self.imdb_id is not None:
            d["imdb_id"] = self.imdb_id
        if self.overview is not None:
            d["overview"] = self.overview
        if self.original_title is not None:
            d["original_title"] = self.original_title
        if self.vote_average is not None:
            d["vote_average"] = self.vote_average
        if self.runtime_minutes is not None:
            d["runtime_minutes"] = self.runtime_minutes
        if self.tmdb_genres:
            d["tmdb_genres"] = self.tmdb_genres
        if self.backdrop_path is not None:
            d["backdrop_path"] = self.backdrop_path
        if self.name is not None:
            d["name"] = self.name
        if self.year is not None:
            d["year"] = self.year
        if self.cover_path_small is not None:
            d["cover_path_small"] = self.cover_path_small
        if self.cover_path_large is not None:
            d["cover_path_large"] = self.cover_path_large
        if self.enrichment_sources:
            d["enrichment_sources"] = self.enrichment_sources
        d["enriched_at"] = self.enriched_at or datetime.now(timezone.utc).isoformat()
        d["enrichment_error"] = None
        return d


def _download_cover(url: str, dest_path: Path) -> bool:
    """Baixa imagem de url para dest_path."""
    import requests as req
    try:
        r = req.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 100:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False


def enrich_video_item(item: dict) -> VideoEnrichmentResult:
    """Enriquecimento TMDB completo para filmes e séries em library_imports."""
    from ..tmdb_enrichment import enrich

    result = VideoEnrichmentResult()
    sources: list[str] = []

    name = (item.get("name") or "").strip()
    content_type = (item.get("content_type") or "movies").strip().lower()
    year = item.get("year")

    if not name:
        result.enriched_at = datetime.now(timezone.utc).isoformat()
        return result

    enriched = enrich(name, content_type, year)

    if enriched.tmdb_id:
        result.tmdb_id = enriched.tmdb_id
        result.imdb_id = enriched.imdb_id
        result.overview = enriched.overview
        result.original_title = enriched.original_title
        result.vote_average = enriched.vote_average
        result.runtime_minutes = enriched.runtime
        result.tmdb_genres = enriched.genres or []
        result.backdrop_path = enriched.backdrop_url
        sources.append("tmdb")

        if enriched.title and enriched.title != name:
            result.name = enriched.title
        if enriched.year and not year:
            result.year = enriched.year

        # Buscar capa se o item não tem (downloads em paralelo)
        if not item.get("cover_path_small") and enriched.poster_url:
            from concurrent.futures import ThreadPoolExecutor

            from ..deps import get_settings
            try:
                covers_path = get_settings().covers_path
                import_id = item.get("id", 0)
                small_file = covers_path / f"import_{import_id}_small.jpg"
                large_file = covers_path / f"import_{import_id}_large.jpg"

                poster_small = enriched.poster_url
                poster_large = enriched.poster_url.replace("/w500", "/w780") if enriched.poster_url else None

                with ThreadPoolExecutor(max_workers=2) as pool:
                    f_small = pool.submit(_download_cover, poster_small, small_file)
                    f_large = pool.submit(_download_cover, poster_large, large_file) if poster_large else None
                    if f_small.result():
                        result.cover_path_small = str(small_file)
                    if f_large and f_large.result():
                        result.cover_path_large = str(large_file)
                    elif result.cover_path_small:
                        result.cover_path_large = result.cover_path_small
            except Exception as e:
                logger.debug("Cover download error: %s", e)

    result.enrichment_sources = sources
    result.enriched_at = datetime.now(timezone.utc).isoformat()
    return result
