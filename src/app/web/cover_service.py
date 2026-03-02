"""Serviço de capas: iTunes (música) e TMDB (filmes/séries) com ranking e URLs pequena/grande."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import requests

from ..deps import get_settings
from ..metadata_from_name import parse_metadata_from_name

# Número de resultados a buscar antes de ranquear
TMDB_SEARCH_LIMIT = 10
ITUNES_SEARCH_LIMIT = 10
# Score mínimo para aceitar o melhor resultado (0–1)
TMDB_SCORE_THRESHOLD = 0.35


def _text_similarity(a: str, b: str) -> float:
    """Similaridade entre duas strings (0–1). Usa SequenceMatcher."""
    if not a or not b:
        return 0.0
    a = a.lower().strip()
    b = b.lower().strip()
    return SequenceMatcher(None, a, b).ratio()


@dataclass
class CoverUrls:
    """URLs da capa em dois tamanhos."""

    url_small: str | None
    url_large: str | None


def _normalize_query(title: str, max_words: int = 8) -> tuple[str, int | None]:
    """Usa metadados do nome para obter query de busca e ano. Retorna (query, year)."""
    meta = parse_metadata_from_name(title or "")
    query = meta.for_search(max_words=max_words)
    return query, meta.year


def _normalize_query_with_fallback(title: str, max_words: int = 8, fallback_words: int = 4) -> tuple[str, int | None, str]:
    """Retorna (query, year, fallback_query). Fallback é nome mais enxuto (ex.: só 'Fringe') para nova tentativa."""
    meta = parse_metadata_from_name(title or "")
    query = meta.for_search(max_words=max_words)
    fallback = meta.for_search_fallback(max_words=fallback_words)
    return query, meta.year, fallback


def _itunes_search_music(term: str) -> list[dict]:
    """Uma chamada de busca iTunes (música). Retorna lista de resultados ou vazia."""
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": term, "media": "music", "limit": ITUNES_SEARCH_LIMIT},
            timeout=5,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get("results") or []
    except Exception:
        return []


def get_cover_urls_music(title: str) -> CoverUrls:
    """Busca capa de álbum/artista no iTunes Search. Query limpa por regex; fallback com nome enxuto."""
    query, _, fallback = _normalize_query_with_fallback(title, max_words=5, fallback_words=4)
    for term in (query, fallback):
        if not (term or "").strip():
            continue
        results = _itunes_search_music(term)
        if not results:
            continue
        term_lower = term.lower()
        best: dict | None = None
        best_score = 0.0
        for item in results:
            name = (item.get("collectionName") or item.get("trackName") or "").strip()
            if not name:
                continue
            score = _text_similarity(term_lower, name.lower())
            if score > best_score:
                best_score = score
                best = item
        if not best:
            best = results[0]
        url = best.get("artworkUrl100") or best.get("artworkUrl60")
        if not url:
            continue
        url_small = re.sub(r"100x100bb", "300x300bb", url, flags=re.I)
        url_small = re.sub(r"60x60bb", "300x300bb", url_small, flags=re.I)
        url_large = re.sub(r"100x100bb", "1000x1000bb", url, flags=re.I)
        url_large = re.sub(r"60x60bb", "1000x1000bb", url_large, flags=re.I)
        return CoverUrls(url_small=url_small, url_large=url_large)
    return CoverUrls(url_small=None, url_large=None)


def _tmdb_search_one(query: str, search_type: str, api_key: str, use_year: int | None) -> list[dict]:
    """Uma chamada de busca TMDB. Retorna lista de resultados ou vazia."""
    try:
        params = {"api_key": api_key, "query": query, "language": "pt-BR"}
        if use_year is not None:
            params["year"] = use_year
        r = requests.get(
            "https://api.themoviedb.org/3/search/" + search_type,
            params=params,
            timeout=5,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get("results") or []
    except Exception:
        return []


def _get_best_tmdb_search_result(title: str, content_type: str, year: int | None = None) -> dict | None:
    """Busca no TMDB com ranking; usa query limpa (regex). Se não achar, tenta fallback (nome enxuto)."""
    s = get_settings()
    api_key = (s.tmdb_api_key or "").strip()
    if not api_key:
        return None

    query, parsed_year, fallback_query = _normalize_query_with_fallback(title, max_words=8, fallback_words=4)
    use_year = year if year is not None else parsed_year
    search_type = "movie" if content_type == "movies" else "tv"

    for attempt_query in (query, fallback_query):
        if not (attempt_query or "").strip():
            continue
        results = _tmdb_search_one(attempt_query, search_type, api_key, use_year)
        if not results:
            continue
        query_lower = attempt_query.lower()
        title_key = "title" if search_type == "movie" else "name"
        scored: list[tuple[float, dict]] = []
        popularities = [float((x.get("popularity") or 0)) for x in results]
        max_pop = max(popularities) if popularities else 1.0
        min_pop = min(popularities) if popularities else 0.0
        pop_range = max_pop - min_pop if max_pop > min_pop else 1.0
        for item in results:
            name = (item.get(title_key) or "").strip()
            sim = _text_similarity(query_lower, name.lower()) if name else 0.0
            year_match = 1.0 if (use_year is not None and item.get("release_date") and str(use_year) in (item.get("release_date") or "")[:4]) else 0.0
            if search_type == "tv" and item.get("first_air_date"):
                year_match = 1.0 if (use_year is not None and str(use_year) in (item.get("first_air_date") or "")[:4]) else 0.0
            pop = float(item.get("popularity") or 0)
            pop_norm = (pop - min_pop) / pop_range if pop_range else 0.0
            score = 0.6 * sim + 0.3 * year_match + 0.1 * pop_norm
            scored.append((score, item))
        scored.sort(key=lambda x: -x[0])
        best_score, best = scored[0]
        if best_score < TMDB_SCORE_THRESHOLD and len(results) > 1:
            best = results[0]
        return best
    return None


def get_tmdb_detail(tmdb_id: int, content_type: str) -> dict | None:
    """Busca detalhes no TMDB por id. Retorna dict com overview, genres, runtime, poster_url, etc."""
    s = get_settings()
    api_key = (s.tmdb_api_key or "").strip()
    if not api_key:
        return None

    resource = "movie" if content_type == "movies" else "tv"
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/{resource}/{tmdb_id}",
            params={"api_key": api_key, "language": "pt-BR"},
            timeout=5,
        )
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception:
        return None

    base_img = "https://image.tmdb.org/t/p"
    poster_path = data.get("poster_path")
    backdrop_path = data.get("backdrop_path")
    poster_url = f"{base_img}/w500{poster_path}" if poster_path else None
    backdrop_url = f"{base_img}/w780{backdrop_path}" if backdrop_path else None

    genres = [g.get("name") for g in (data.get("genres") or []) if g.get("name")]

    if content_type == "movies":
        return {
            "id": data.get("id"),
            "title": data.get("title") or data.get("original_title"),
            "overview": data.get("overview") or "",
            "genres": genres,
            "runtime": data.get("runtime"),
            "release_date": (data.get("release_date") or "")[:10] or None,
            "vote_average": data.get("vote_average"),
            "poster_url": poster_url,
            "backdrop_url": backdrop_url,
        }
    # tv
    return {
        "id": data.get("id"),
        "title": data.get("name") or data.get("original_name"),
        "overview": data.get("overview") or "",
        "genres": genres,
        "number_of_seasons": data.get("number_of_seasons"),
        "number_of_episodes": data.get("number_of_episodes"),
        "first_air_date": (data.get("first_air_date") or "")[:10] or None,
        "vote_average": data.get("vote_average"),
        "poster_url": poster_url,
        "backdrop_url": backdrop_url,
    }


def get_search_filter_suggestions(content_type: str, query: str) -> dict:
    """
    Retorna sugestões de filtros (anos, gêneros) a partir de TMDB ou iTunes.
    Cache Redis TTL 1 dia.
    """
    meta = parse_metadata_from_name(query or "")
    q = meta.for_search(max_words=8)
    if not q:
        return {"years": [], "genres": [], "qualities": []}
    from ..deps import get_cover_cache
    from .cover_cache import COVER_SEARCH_TTL_SECONDS, SEARCH_PREFIX
    cache_key = f"{SEARCH_PREFIX}filter-suggestions:{content_type}:{q.strip().lower()[:150]}"
    cache = get_cover_cache()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    years: list[int] = []
    genres: list[str] = []

    if content_type in ("movies", "tv"):
        s = get_settings()
        api_key = (s.tmdb_api_key or "").strip()
        if api_key:
            search_type = "movie" if content_type == "movies" else "tv"
            try:
                r = requests.get(
                    f"https://api.themoviedb.org/3/search/{search_type}",
                    params={"api_key": api_key, "query": q, "language": "pt-BR"},
                    timeout=5,
                )
                if r.status_code == 200:
                    data = r.json()
                    results = data.get("results") or []
                    for item in results:
                        date_str = item.get("release_date") or item.get("first_air_date") or ""
                        if len(date_str) >= 4:
                            try:
                                y = int(date_str[:4])
                                if 1900 <= y <= 2100 and y not in years:
                                    years.append(y)
                            except ValueError:
                                pass
                    years.sort()
                    genre_ids: set[int] = set()
                    for item in results:
                        for gid in item.get("genre_ids") or []:
                            genre_ids.add(gid)
                    if genre_ids:
                        gr = requests.get(
                            f"https://api.themoviedb.org/3/genre/{search_type}/list",
                            params={"api_key": api_key, "language": "pt-BR"},
                            timeout=5,
                        )
                        if gr.status_code == 200:
                            gdata = gr.json()
                            id_to_name = {g["id"]: g["name"] for g in (gdata.get("genres") or [])}
                            for gid in sorted(genre_ids):
                                if gid in id_to_name and id_to_name[gid] not in genres:
                                    genres.append(id_to_name[gid])
            except Exception:
                pass

    if content_type == "music":
        try:
            r = requests.get(
                "https://itunes.apple.com/search",
                params={"term": q, "media": "music", "limit": 15},
                timeout=5,
            )
            if r.status_code == 200:
                data = r.json()
                for item in (data.get("results") or []):
                    g = (item.get("primaryGenreName") or "").strip()
                    if g and g not in genres:
                        genres.append(g)
                    rd = item.get("releaseDate") or ""
                    if len(rd) >= 4:
                        try:
                            y = int(rd[:4])
                            if 1900 <= y <= 2100 and y not in years:
                                years.append(y)
                        except ValueError:
                            pass
                years.sort()
        except Exception:
            pass

    qualities = ["720p", "1080p", "2160p", "4K", "FLAC", "320", "V0", "V2"]
    out = {"years": years[:20], "genres": genres[:25], "qualities": qualities}
    cache.set(cache_key, out, ttl_seconds=COVER_SEARCH_TTL_SECONDS)
    return out


def get_tmdb_detail_by_title(title: str, content_type: str, year: int | None = None) -> dict | None:
    """Resolve título para o melhor match TMDB e retorna detalhes. Cache Redis TTL 1 dia."""
    if content_type not in ("movies", "tv"):
        return None
    from ..deps import get_cover_cache
    from .cover_cache import COVER_SEARCH_TTL_SECONDS, SEARCH_PREFIX
    meta = parse_metadata_from_name(title or "")
    q = (meta.for_search(max_words=8) or (title or "")[:150]).strip().lower()
    cache_key = f"{SEARCH_PREFIX}tmdb-detail:{content_type}:{q}:{year or ''}"
    cache = get_cover_cache()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    best = _get_best_tmdb_search_result(title, content_type, year)
    if not best:
        return None
    tmdb_id = best.get("id")
    if tmdb_id is None:
        return None
    result = get_tmdb_detail(int(tmdb_id), content_type)
    if result:
        cache.set(cache_key, result, ttl_seconds=COVER_SEARCH_TTL_SECONDS)
    return result


def get_cover_urls_tmdb(title: str, content_type: str) -> CoverUrls:
    """Busca poster no TMDB (movies ou tv) com ranking. Retorna URLs pequena (w300) e grande (w500)."""
    best = _get_best_tmdb_search_result(title, content_type)
    if not best:
        return CoverUrls(url_small=None, url_large=None)
    poster_path = best.get("poster_path")
    if not poster_path:
        return CoverUrls(url_small=None, url_large=None)
    base = "https://image.tmdb.org/t/p"
    return CoverUrls(
        url_small=f"{base}/w300{poster_path}",
        url_large=f"{base}/w500{poster_path}",
    )


def _itunes_search_movie_tv(term: str, media: str, entity: str) -> list[dict]:
    """Uma chamada de busca iTunes (movie ou tvShow). Retorna lista de resultados ou vazia."""
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": term, "media": media, "entity": entity, "limit": ITUNES_SEARCH_LIMIT},
            timeout=5,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get("results") or []
    except Exception:
        return []


def _get_best_itunes_movie_or_tv_result(title: str, media: str, entity: str) -> tuple[float, dict | None]:
    """
    Busca no iTunes (media=movie ou tvShow) com ranking. Query limpa por regex; fallback com nome enxuto.
    Retorna (score, item) do melhor resultado.
    """
    query, _, fallback = _normalize_query_with_fallback(title, max_words=8, fallback_words=4)
    for term in (query, fallback):
        if not (term or "").strip():
            continue
        results = _itunes_search_movie_tv(term, media, entity)
        if not results:
            continue
        term_lower = term.lower()
        best_score = 0.0
        best_item: dict | None = None
        for item in results:
            name = (item.get("trackName") or item.get("collectionName") or item.get("trackCensoredName") or "").strip()
            if not name:
                continue
            score = _text_similarity(term_lower, name.lower())
            if score > best_score:
                best_score = score
                best_item = item
        if not best_item:
            best_item = results[0]
            best_score = _text_similarity(term_lower, (best_item.get("trackName") or best_item.get("collectionName") or "").lower())
        return best_score, best_item
    return 0.0, None


def _itunes_artwork_to_cover_urls(item: dict | None) -> CoverUrls:
    """Extrai URLs pequena (300) e grande (1000) do artwork do resultado iTunes."""
    if not item:
        return CoverUrls(url_small=None, url_large=None)
    url = item.get("artworkUrl100") or item.get("artworkUrl60")
    if not url:
        return CoverUrls(url_small=None, url_large=None)
    url_small = re.sub(r"100x100bb", "300x300bb", url, flags=re.I)
    url_small = re.sub(r"60x60bb", "300x300bb", url_small, flags=re.I)
    url_large = re.sub(r"100x100bb", "1000x1000bb", url, flags=re.I)
    url_large = re.sub(r"60x60bb", "1000x1000bb", url_large, flags=re.I)
    return CoverUrls(url_small=url_small, url_large=url_large)


def get_cover_urls_itunes_movie(title: str) -> CoverUrls:
    """Busca capa de filme no iTunes Search (media=movie). Usa título normalizado e ranking."""
    _, item = _get_best_itunes_movie_or_tv_result(title, "movie", "movie")
    return _itunes_artwork_to_cover_urls(item)


def get_cover_urls_itunes_tv(title: str) -> CoverUrls:
    """Busca capa de série no iTunes Search (media=tvShow). Usa título normalizado e ranking."""
    _, item = _get_best_itunes_movie_or_tv_result(title, "tvShow", "tvSeason")
    return _itunes_artwork_to_cover_urls(item)


def _get_cover_urls_movies_tv_best_match(title: str, content_type: str) -> CoverUrls:
    """
    Consulta TMDB e iTunes para filmes/séries; escolhe o melhor por score (similaridade + ano).
    Garante que o nome usado na busca tem metadados removidos (já feito em _normalize_query).
    """
    query, parsed_year = _normalize_query(title, max_words=8)
    if not query:
        return CoverUrls(url_small=None, url_large=None)

    urls_tmdb = get_cover_urls_tmdb(title, content_type)
    if content_type == "movies":
        urls_itunes = get_cover_urls_itunes_movie(title)
    else:
        urls_itunes = get_cover_urls_itunes_tv(title)

    # Score TMDB: reutilizar o melhor resultado para obter um score
    best_tmdb = _get_best_tmdb_search_result(title, content_type)
    title_key = "title" if content_type == "movies" else "name"
    tmdb_name = (best_tmdb.get(title_key) or "").strip() if best_tmdb else ""
    score_tmdb = _text_similarity(query.lower(), tmdb_name.lower()) if tmdb_name else 0.0
    if parsed_year is not None and best_tmdb:
        release = (best_tmdb.get("release_date") or best_tmdb.get("first_air_date") or "")[:4]
        if release and str(parsed_year) == release:
            score_tmdb += 0.2
    score_tmdb = min(1.0, score_tmdb)

    score_itunes, itunes_item = _get_best_itunes_movie_or_tv_result(
        title, "movie" if content_type == "movies" else "tvShow",
        "movie" if content_type == "movies" else "tvSeason",
    )
    if parsed_year is not None and itunes_item and itunes_item.get("releaseDate"):
        release = (itunes_item.get("releaseDate") or "")[:4]
        if release and str(parsed_year) == release:
            score_itunes += 0.2
    score_itunes = min(1.0, score_itunes)

    has_tmdb = urls_tmdb.url_small or urls_tmdb.url_large
    has_itunes = urls_itunes.url_small or urls_itunes.url_large
    if has_tmdb and (not has_itunes or score_tmdb >= score_itunes):
        return urls_tmdb
    if has_itunes:
        return urls_itunes
    return urls_tmdb if has_tmdb else urls_itunes


def _cover_cache_key(content_type: str, title: str) -> str:
    """Chave estável para cache pesquisa: content_type + título normalizado. TTL máx 1 dia."""
    from .cover_cache import _cache_key
    meta = parse_metadata_from_name(title or "")
    q = meta.for_search(max_words=8)
    return _cache_key(content_type, q or (title or "")[:200])


def get_cover_urls(content_type: str, title: str) -> CoverUrls:
    """
    Retorna URLs da capa (pequena e grande). Usa cache Redis (pesquisa, TTL 1 dia) quando disponível.
    Música: apenas iTunes. Filmes/Séries: TMDB e iTunes; best match.
    """
    if not title or not title.strip():
        return CoverUrls(url_small=None, url_large=None)
    from ..deps import get_cover_cache
    from .cover_cache import COVER_SEARCH_TTL_SECONDS
    cache = get_cover_cache()
    key = _cover_cache_key(content_type, title)
    cached = cache.get(key)
    if cached is not None:
        return CoverUrls(url_small=cached.get("url_small"), url_large=cached.get("url_large"))
    if content_type == "music":
        urls = get_cover_urls_music(title)
    elif content_type in ("movies", "tv"):
        urls = _get_cover_urls_movies_tv_best_match(title, content_type)
    else:
        urls = CoverUrls(url_small=None, url_large=None)
    if urls.url_small or urls.url_large:
        cache.set(key, {"url_small": urls.url_small, "url_large": urls.url_large}, ttl_seconds=COVER_SEARCH_TTL_SECONDS)
    return urls


def get_cover_url(content_type: str, title: str) -> str | None:
    """Retorna URL da capa (tamanho pequeno) para compatibilidade. Música: iTunes; Filmes/Séries: TMDB."""
    urls = get_cover_urls(content_type, title)
    return urls.url_small


def _download_image(url: str, path: str) -> bool:
    """Baixa imagem de url para path. Retorna True se sucesso."""
    try:
        r = requests.get(url, timeout=10, stream=True)
        if r.status_code != 200:
            return False
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception:
        return False


def fetch_and_cache_cover(download_id: int, content_type: str, title: str) -> CoverUrls:
    """
    Busca capa (com ranking), baixa para a pasta de cache e atualiza o registro no DB.
    Grava também no Redis com chave dl-torrent:cover:download:{id} (TTL 7 dias, eviction controla).
    """
    from ..deps import get_cover_cache, get_repo
    from .cover_cache import COVER_DOWNLOAD_TTL_SECONDS, download_cache_key

    urls = get_cover_urls(content_type, title)
    if not urls.url_small and not urls.url_large:
        return urls

    s = get_settings()
    covers_path = s.covers_path
    covers_path.mkdir(parents=True, exist_ok=True)
    small_path: str | None = None
    large_path: str | None = None

    if urls.url_small:
        small_file = covers_path / f"{download_id}_small.jpg"
        if _download_image(urls.url_small, str(small_file)):
            small_path = str(small_file)
    if urls.url_large and urls.url_large != urls.url_small:
        large_file = covers_path / f"{download_id}_large.jpg"
        if _download_image(urls.url_large, str(large_file)):
            large_path = str(large_file)
    elif small_path and not large_path:
        large_path = small_path

    if small_path or large_path:
        get_repo().set_cover_paths(download_id, cover_path_small=small_path, cover_path_large=large_path)
        cache = get_cover_cache()
        cache.set(
            download_cache_key(download_id),
            {"url_small": urls.url_small, "url_large": urls.url_large},
            ttl_seconds=COVER_DOWNLOAD_TTL_SECONDS,
        )

    return urls


def evict_cover_for_download(download_id: int) -> None:
    """Remove do Redis a capa do download e apaga os arquivos em covers_dir."""
    from ..deps import get_cover_cache
    cache = get_cover_cache()
    cache.evict_download(download_id)
    s = get_settings()
    for name in (f"{download_id}_small.jpg", f"{download_id}_large.jpg"):
        p = s.covers_path / name
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass
