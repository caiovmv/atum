"""Enriquecimento via TMDB: busca detalhes de filmes/séries incluindo IMDB ID."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import requests

from .deps import get_settings
from .metadata_from_name import parse_metadata_from_name
from .web.cover_service import get_best_tmdb_search_result

logger = logging.getLogger(__name__)


@dataclass
class EnrichedMetadata:
    """Metadados enriquecidos via TMDB."""

    title: str | None = None
    original_title: str | None = None
    year: int | None = None
    tmdb_id: int | None = None
    imdb_id: str | None = None
    overview: str | None = None
    genres: list[str] = field(default_factory=list)
    poster_url: str | None = None
    backdrop_url: str | None = None
    vote_average: float | None = None
    runtime: int | None = None
    number_of_seasons: int | None = None
    number_of_episodes: int | None = None
    content_type: str | None = None


def _tmdb_api_key() -> str | None:
    """Obtém TMDB API key: primeiro do settings_repo (runtime), depois do .env."""
    from .deps import get_settings_repo
    repo = get_settings_repo()
    if repo:
        key = repo.get("tmdb_api_key")
        if key and str(key).strip():
            return str(key).strip()
    s = get_settings()
    return (s.tmdb_api_key or "").strip() or None


def _get_imdb_id_for_tv(tmdb_id: int, api_key: str) -> str | None:
    """Busca IMDB ID para séries via /tv/{id}/external_ids."""
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids",
            params={"api_key": api_key},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("imdb_id") or None
    except Exception:
        pass
    return None


def _get_movie_detail(tmdb_id: int, api_key: str) -> dict | None:
    """Busca detalhes de um filme no TMDB."""
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}",
            params={"api_key": api_key, "language": "pt-BR"},
            timeout=8,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _get_tv_detail(tmdb_id: int, api_key: str) -> dict | None:
    """Busca detalhes de uma série no TMDB."""
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/tv/{tmdb_id}",
            params={"api_key": api_key, "language": "pt-BR"},
            timeout=8,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def enrich_movie(title: str, year: int | None = None) -> EnrichedMetadata:
    """Enriquece metadados de um filme via TMDB. Retorna titulo oficial, ano, tmdb_id, imdb_id, generos, poster."""
    api_key = _tmdb_api_key()
    if not api_key:
        return EnrichedMetadata(title=title, year=year, content_type="movies")

    best = get_best_tmdb_search_result(title, "movies", year)
    if not best:
        return EnrichedMetadata(title=title, year=year, content_type="movies")

    tmdb_id = best.get("id")
    if not tmdb_id:
        return EnrichedMetadata(title=title, year=year, content_type="movies")

    detail = _get_movie_detail(int(tmdb_id), api_key)
    if not detail:
        release_date = best.get("release_date") or ""
        parsed_year = int(release_date[:4]) if len(release_date) >= 4 else year
        return EnrichedMetadata(
            title=best.get("title") or title,
            year=parsed_year,
            tmdb_id=int(tmdb_id),
            content_type="movies",
        )

    release_date = (detail.get("release_date") or "")[:10]
    det_year = int(release_date[:4]) if len(release_date) >= 4 else year
    base_img = "https://image.tmdb.org/t/p"
    poster_path = detail.get("poster_path")
    backdrop_path = detail.get("backdrop_path")
    genres = [g.get("name") for g in (detail.get("genres") or []) if g.get("name")]

    return EnrichedMetadata(
        title=detail.get("title") or detail.get("original_title") or title,
        original_title=detail.get("original_title"),
        year=det_year,
        tmdb_id=int(tmdb_id),
        imdb_id=detail.get("imdb_id") or None,
        overview=detail.get("overview") or None,
        genres=genres,
        poster_url=f"{base_img}/w500{poster_path}" if poster_path else None,
        backdrop_url=f"{base_img}/w780{backdrop_path}" if backdrop_path else None,
        vote_average=detail.get("vote_average"),
        runtime=detail.get("runtime"),
        content_type="movies",
    )


def enrich_tv(title: str, year: int | None = None) -> EnrichedMetadata:
    """Enriquece metadados de uma série via TMDB. Busca IMDB ID via external_ids."""
    api_key = _tmdb_api_key()
    if not api_key:
        return EnrichedMetadata(title=title, year=year, content_type="tv")

    best = get_best_tmdb_search_result(title, "tv", year)
    if not best:
        return EnrichedMetadata(title=title, year=year, content_type="tv")

    tmdb_id = best.get("id")
    if not tmdb_id:
        return EnrichedMetadata(title=title, year=year, content_type="tv")

    detail = _get_tv_detail(int(tmdb_id), api_key)
    imdb_id = _get_imdb_id_for_tv(int(tmdb_id), api_key)

    if not detail:
        first_air = best.get("first_air_date") or ""
        parsed_year = int(first_air[:4]) if len(first_air) >= 4 else year
        return EnrichedMetadata(
            title=best.get("name") or title,
            year=parsed_year,
            tmdb_id=int(tmdb_id),
            imdb_id=imdb_id,
            content_type="tv",
        )

    first_air = (detail.get("first_air_date") or "")[:10]
    det_year = int(first_air[:4]) if len(first_air) >= 4 else year
    base_img = "https://image.tmdb.org/t/p"
    poster_path = detail.get("poster_path")
    backdrop_path = detail.get("backdrop_path")
    genres = [g.get("name") for g in (detail.get("genres") or []) if g.get("name")]

    return EnrichedMetadata(
        title=detail.get("name") or detail.get("original_name") or title,
        original_title=detail.get("original_name"),
        year=det_year,
        tmdb_id=int(tmdb_id),
        imdb_id=imdb_id,
        overview=detail.get("overview") or None,
        genres=genres,
        poster_url=f"{base_img}/w500{poster_path}" if poster_path else None,
        backdrop_url=f"{base_img}/w780{backdrop_path}" if backdrop_path else None,
        vote_average=detail.get("vote_average"),
        number_of_seasons=detail.get("number_of_seasons"),
        number_of_episodes=detail.get("number_of_episodes"),
        content_type="tv",
    )


def enrich(title: str, content_type: str, year: int | None = None) -> EnrichedMetadata:
    """Enriquece metadados pelo tipo. Para music retorna dados mínimos (enriquecimento musical usa iTunes/mutagen)."""
    ct = (content_type or "").strip().lower()
    if ct == "movies":
        return enrich_movie(title, year)
    if ct == "tv":
        return enrich_tv(title, year)
    meta = parse_metadata_from_name(title or "")
    return EnrichedMetadata(
        title=meta.cleaned_title or title,
        year=meta.year or year,
        content_type="music",
    )
