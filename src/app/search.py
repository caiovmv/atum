"""Busca em indexadores (1337x, TPB, TG, YTS, EZTV, NYAA, etc.) e envio para cliente."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import typer

import py1337x

# Indexadores disponíveis: 1337x, tpb, tg, yts, eztv, nyaa, limetorrents, torlock, speedtorrent, fitgirl, rutracker, iptorrents
ALL_INDEXERS = frozenset({
    "1337x", "tpb", "tg",
    "yts", "eztv", "nyaa", "limetorrents", "torlock", "speedtorrent", "fitgirl", "rutracker", "iptorrents",
})
# Por padrão busca em todos os indexadores públicos (iptorrents é privado e não implementado)
DEFAULT_INDEXERS = ["1337x", "tpb", "tg", "yts", "eztv", "nyaa", "limetorrents", "torlock", "speedtorrent", "fitgirl", "rutracker"]

from .config import get_settings
from .destinations import resolve_destination
from .quality import (
    QualityInfo,
    is_acceptable,
    matches_format,
    parse_format_filter,
    parse_quality,
)
from .organize import ContentType
from .quality_video import (
    VideoQualityInfo,
    matches_format_video,
    parse_format_filter_video,
    parse_quality_video,
)


@dataclass
class SearchResult:
    """Um resultado de busca já filtrado por qualidade (áudio ou vídeo)."""

    title: str
    quality: Union[QualityInfo, VideoQualityInfo]
    seeders: int
    size: str
    torrent_id: str
    indexer: str = "1337x"
    magnet: str | None = None  # TPB retorna na busca; 1337x preenche depois via get_magnet_1337x
    leechers: int = 0


def result_to_dict(result: SearchResult) -> dict:
    """Serializa SearchResult para dict (JSON) para uso na API."""
    return {
        "title": result.title,
        "quality_label": result.quality.label,
        "seeders": result.seeders,
        "leechers": result.leechers,
        "size": result.size,
        "size_bytes": _parse_size_to_bytes(result.size),
        "torrent_id": result.torrent_id,
        "indexer": result.indexer,
        "magnet": result.magnet,
    }


def _parse_seeders(s: str) -> int:
    try:
        return int(str(s).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def _parse_size_to_bytes(size_str: str) -> float:
    """Converte string de tamanho (ex: '21.6 GB', '1.2 MB') para bytes. Retorna 0 se inválido."""
    import re
    s = (size_str or "").strip()
    if not s:
        return 0.0
    m = re.match(r"^([\d.,]+)\s*([KMGTP]?B?|kB|MB|GB|TB)$", s, re.I)
    if not m:
        return 0.0
    try:
        num = float(m.group(1).replace(",", "."))
    except ValueError:
        return 0.0
    unit = (m.group(2) or "").upper().replace("B", "").strip() or "B"
    multipliers = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}
    return num * multipliers.get(unit, 1)


def get_1337x_client(settings=None):
    """Retorna uma instância do cliente 1337x (único ponto de criação, reutilizável)."""
    from .config import Settings

    s = settings or get_settings()
    base_url = (getattr(s, "x1337_base_url", "") or "").strip()
    kwargs = {"base_url": base_url} if base_url else {}
    return py1337x.Py1337x(**kwargs)


def _category_1337x(content_type: ContentType | None) -> str | None:
    """Retorna categoria 1337x para o content_type; None = todas."""
    if content_type == "music":
        return py1337x.category.MUSIC
    if content_type == "movies":
        return py1337x.category.MOVIES
    if content_type == "tv":
        return py1337x.category.TV
    return None


def _quality_filter_for_content_type(
    content_type: ContentType,
    format_filter: str | None,
    no_quality_filter: bool,
) -> tuple[bool, set[str] | None]:
    """Retorna (use_video, allowed) para o content_type e filtro. DRY para 1337x/TPB/TG."""
    use_video = content_type in ("movies", "tv")
    allowed = None if no_quality_filter else (
        parse_format_filter_video(format_filter) if use_video else parse_format_filter(format_filter)
    )
    return use_video, allowed


def search_1337x(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
) -> list[SearchResult]:
    """Busca no 1337x; categoria conforme content_type; solicita várias páginas até atingir limit."""
    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    category = None if not music_category_only else _category_1337x(content_type)

    try:
        torrents = get_1337x_client()
    except Exception as e:
        if verbose:
            typer.echo(f"[verbose] Erro na busca 1337x: {type(e).__name__}: {e}")
        return []

    results: list[SearchResult] = []
    page = 1
    cat_label = category or "todas as categorias"
    while True:
        try:
            kwargs: dict = {"page": page, "sort_by": py1337x.sort.SEEDERS}
            if category:
                kwargs["category"] = category
            raw = torrents.search(query, **kwargs)
        except Exception as e:
            if verbose:
                typer.echo(f"[verbose] Erro 1337x página {page}: {type(e).__name__}: {e}")
            break
        items = getattr(raw, "items", None)
        if verbose and items:
            typer.echo(f"[verbose] 1337x página {page}: {len(items)} item(ns) para '{query}' ({cat_label}).")
        if not items:
            break
        for item in raw.items:
            title = getattr(item, "name", "") or ""
            if use_video:
                quality = parse_quality_video(title)
                if not no_quality_filter and not matches_format_video(quality, allowed):
                    continue
            else:
                quality = parse_quality(title)
                if not no_quality_filter and not matches_format(quality, allowed):
                    continue
            seeders = _parse_seeders(getattr(item, "seeders", 0))
            leechers = _parse_seeders(getattr(item, "leechers", 0))
            size = getattr(item, "size", "") or ""
            tid = getattr(item, "torrent_id", "") or ""
            results.append(
                SearchResult(
                    title=title,
                    quality=quality,
                    seeders=seeders,
                    size=size,
                    torrent_id=tid,
                    leechers=leechers,
                )
            )
        if len(results) >= limit:
            break
        page_count = getattr(raw, "page_count", None)
        if page_count is not None and page >= page_count:
            break
        page += 1
        if page > 20:
            break

    results.sort(key=lambda r: (-r.quality.score, -r.seeders))
    out = results[:limit]
    if verbose:
        typer.echo(f"[verbose] 1337x: {len(out)} resultado(s) após filtro de qualidade.")
    return out


def get_magnet_1337x(torrent_id: str) -> str | None:
    """Obtém o link magnet para um torrent_id do 1337x."""
    if not torrent_id:
        return None
    try:
        torrents = get_1337x_client()
        info = torrents.info(torrent_id=torrent_id)
        return getattr(info, "magnet_link", None) or None
    except Exception:
        return None


def _category_tpb(content_type: ContentType):
    """Retorna categoria TPB para o content_type."""
    from tpblite import CATEGORIES
    if content_type == "music":
        return CATEGORIES.AUDIO.MUSIC
    if content_type == "movies":
        return CATEGORIES.VIDEO.MOVIES
    if content_type == "tv":
        return CATEGORIES.VIDEO.TV_SHOWS
    return None


def _apply_tpblite_patches() -> None:
    """Aplica patches na tpblite para tolerar HTML/valores que quebram o parsing (ex.: tamanho com \\xa0, ordem de colunas)."""
    import re
    try:
        from tpblite.models import torrents as tpb_models
    except ImportError:
        return
    _orig_size = getattr(tpb_models, "fileSizeStrToInt", None)
    if _orig_size is not None:

        def _patched_file_size(size_str: str) -> int:
            s = (size_str or "").replace("\xa0", " ").replace("\u00a0", " ").strip()
            if not s:
                return 0
            try:
                return _orig_size(s)
            except Exception:
                m = re.search(r"([\d.,]+)\s*([KMGTP]?i?B)", s, re.I)
                if m:
                    try:
                        num = float(m.group(1).replace(",", "."))
                        unit = m.group(2).upper().replace("B", "").strip() or "B"
                        mult = {"": 1, "K": 2**10, "M": 2**20, "G": 2**30, "T": 2**40, "P": 2**40 * 1024}
                        return int(num * mult.get(unit, 1))
                    except (ValueError, TypeError):
                        pass
                return 0

        tpb_models.fileSizeStrToInt = _patched_file_size

    _Torrent = getattr(tpb_models, "Torrent", None)
    if _Torrent is not None and hasattr(_Torrent, "_getPeers"):
        _orig_peers = _Torrent._getPeers

        def _patched_get_peers(self: object) -> tuple[int, int]:
            try:
                return _orig_peers(self)
            except (ValueError, TypeError, IndexError):
                row = getattr(self, "html_row", None)
                if row is None:
                    return 0, 0
                try:
                    texts = row.xpath('.//td[@align="right"]/text()')
                    nums = []
                    for t in (texts or []):
                        t = str(t).replace("\xa0", " ").strip()
                        if re.match(r"^\d+$", t):
                            nums.append(int(t))
                        if len(nums) >= 2:
                            return nums[0], nums[1]
                except Exception:
                    pass
                return 0, 0

        _Torrent._getPeers = _patched_get_peers

    if _Torrent is not None and hasattr(_Torrent, "_getFileInfo"):
        _orig_file_info = _Torrent._getFileInfo

        def _patched_get_file_info(self: object) -> tuple:
            try:
                return _orig_file_info(self)
            except (IndexError, ValueError, AttributeError):
                row = getattr(self, "html_row", None)
                if row is None:
                    return "", "", ""
                try:
                    texts = row.xpath('.//td[@align="right"]/text()')
                    size_str = ""
                    for t in (texts or []):
                        t = str(t).replace("\xa0", " ").strip()
                        if "MiB" in t or "GiB" in t or "KiB" in t:
                            size_str = t
                            break
                    font_text = "".join(row.xpath('.//font[@class="detDesc"]/descendant::text()'))
                    parts = (font_text or "").split(",")
                    uptime = parts[0].replace("Uploaded ", "").strip() if len(parts) > 0 else ""
                    if not size_str and len(parts) > 1:
                        size_str = parts[1].replace("Size ", "").strip()
                    uploader = parts[2].replace("ULed by ", "").strip() if len(parts) > 2 else ""
                    return uptime, size_str, uploader
                except Exception:
                    return "", "", ""

        _Torrent._getFileInfo = _patched_get_file_info

    if _Torrent is not None and hasattr(_Torrent, "_getUrl"):
        _orig_get_url = _Torrent._getUrl

        def _patched_get_url(self: object) -> str:
            try:
                return _orig_get_url(self) or ""
            except (AttributeError, TypeError):
                row = getattr(self, "html_row", None)
                if row is None:
                    return ""
                tag = row.find('.//a[@class="detLink"]') if hasattr(row, "find") else None
                if tag is not None and hasattr(tag, "get"):
                    return tag.get("href", "") or ""
                return ""

        _Torrent._getUrl = _patched_get_url

    if _Torrent is not None and hasattr(_Torrent, "_getTitle"):
        _orig_get_title = _Torrent._getTitle

        def _patched_get_title(self: object) -> str:
            try:
                out = _orig_get_title(self)
                if out and out.strip():
                    return out
            except Exception:
                pass
            row = getattr(self, "html_row", None)
            if row is None:
                return ""
            if hasattr(row, "findtext"):
                out = row.findtext('.//a[@class="detLink"]')
                if out and out.strip():
                    return out
            try:
                links = row.xpath('.//a[contains(@href, "/torrent/")]')
                if links and len(links) > 0:
                    first = links[0]
                    text = (first.text or "").strip()
                    if not text and hasattr(first, "itertext"):
                        text = "".join(first.itertext()).strip()
                    if text:
                        return text
            except Exception:
                pass
            return ""

        _Torrent._getTitle = _patched_get_title

    if _Torrent is not None and hasattr(_Torrent, "_getMagnetLink"):
        _orig_magnet = _Torrent._getMagnetLink

        def _patched_get_magnet(self: object) -> str:
            try:
                return _orig_magnet(self) or ""
            except (IndexError, AttributeError):
                row = getattr(self, "html_row", None)
                if row is None:
                    return ""
                try:
                    hrefs = row.xpath('.//a[starts-with(@href, "magnet")]/@href')
                    return hrefs[0] if hrefs else ""
                except Exception:
                    return ""

        _Torrent._getMagnetLink = _patched_get_magnet

    _Torrents = getattr(tpb_models, "Torrents", None)
    if _Torrents is not None and _Torrent is not None and hasattr(_Torrents, "_createTorrentList"):
        _orig_create = _Torrents._createTorrentList

        def _patched_create_torrent_list(self: object) -> list:
            root = None
            try:
                import lxml.etree as ET
                html = getattr(self, "html_source", "")
                root = ET.HTML(html) if html else None
            except Exception:
                return []
            if root is None or root.find("body") is None:
                raise ConnectionError("Could not determine torrents (empty html body)")
            rows = root.xpath('//tr[td[@class="vertTh"]]')
            torrents = []
            for row in rows:
                try:
                    torrents.append(_Torrent(row))
                except (ValueError, TypeError, IndexError, AttributeError, KeyError, ConnectionError):
                    continue
            return torrents

        _Torrents._createTorrentList = _patched_create_torrent_list


def search_tpb(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no The Pirate Bay; retorna SearchResult com magnet preenchido."""
    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    category = None if not music_category_only else _category_tpb(content_type)

    _apply_tpblite_patches()

    s = settings or get_settings()
    base_url = (getattr(s, "tpb_base_url", "") or "https://tpb.party").strip()
    try:
        from tpblite import TPB

        t = TPB(base_url)
        kwargs = {}
        if category is not None:
            kwargs["category"] = category
        raw = t.search(query, **kwargs)
    except Exception as e:
        if verbose:
            typer.echo(f"[verbose] Erro na busca TPB: {type(e).__name__}: {e}")
        return []

    if verbose:
        n = len(raw) if raw else 0
        cat = str(category) if category else "todas"
        typer.echo(f"[verbose] TPB retornou {n} resultado(s) para '{query}' ({cat}).")

    results: list[SearchResult] = []
    for torrent in raw:
        title = getattr(torrent, "title", "") or ""
        if use_video:
            quality = parse_quality_video(title)
            if not no_quality_filter and not matches_format_video(quality, allowed):
                continue
        else:
            quality = parse_quality(title)
            if not no_quality_filter and not matches_format(quality, allowed):
                continue
        seeders = int(getattr(torrent, "seeds", 0) or 0)
        leechers = int(getattr(torrent, "leeches", 0) or 0)
        size = getattr(torrent, "filesize", "") or ""
        magnet = getattr(torrent, "magnetlink", "") or None
        tid = getattr(torrent, "infohash", "") or getattr(torrent, "url", "") or ""
        results.append(
            SearchResult(
                title=title,
                quality=quality,
                seeders=seeders,
                size=size,
                torrent_id=tid,
                indexer="tpb",
                magnet=magnet,
                leechers=leechers,
            )
        )

    results.sort(key=lambda r: (-r.quality.score, -r.seeders))
    out = results[:limit]
    if verbose:
        typer.echo(f"[verbose] TPB: após filtro de qualidade: {len(out)} resultado(s) exibidos.")
    return out


def _cat_tg(content_type: ContentType) -> int | None:
    """Retorna cat ID do TorrentGalaxy para o content_type; 99=Music, 1=Movies, 2=TV."""
    if content_type == "music":
        return 99
    if content_type == "movies":
        return 1
    if content_type == "tv":
        return 2
    return None


def search_tg(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no TorrentGalaxy via scraping; retorna SearchResult com magnet quando disponível."""
    import re
    import urllib.parse

    import requests

    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    cat_id = None if not music_category_only else _cat_tg(content_type)

    s = settings or get_settings()
    base = (getattr(s, "tg_base_url", "") or "https://torrentgalaxy.to").strip().rstrip("/")
    search_path = "/torrents.php"
    url = f"{base}{search_path}?search={urllib.parse.quote_plus(query)}"
    if cat_id is not None:
        url += f"&cat={cat_id}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"})
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        if verbose:
            typer.echo(f"[verbose] Erro na busca TorrentGalaxy: {type(e).__name__}: {e}")
        return []

    # TG: parear magnet com título mais próximo (título em title="..." antes do magnet)
    results: list[SearchResult] = []
    magnet_re = re.compile(r'href="(magnet:\?xt=[^"]+)"', re.I)
    title_in_quote = re.compile(r'title="((?:[^"\\]|\\.)*)"', re.I)

    def clean(t: str) -> str:
        t = re.sub(r"<[^>]+>", "", t)
        t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
        return t.strip() or ""

    for m in magnet_re.finditer(html):
        magnet = m.group(1)
        # Título: último title="..." antes desta posição (evita capturar logo/menu)
        before = html[: m.start()]
        titles_before = title_in_quote.findall(before)
        title = clean(titles_before[-1]) if titles_before else f"Torrent"
        # Evitar títulos genéricos (tooltips do site)
        if len(title) < 3 or title.lower() in ("torrent", "download", "magnet", "get"):
            continue
        if use_video:
            quality = parse_quality_video(title)
            if not no_quality_filter and not matches_format_video(quality, allowed):
                continue
        else:
            quality = parse_quality(title)
            if not no_quality_filter and not matches_format(quality, allowed):
                continue
        results.append(
            SearchResult(
                title=title,
                quality=quality,
                seeders=0,
                size="",
                torrent_id=magnet[:80] or "",
                indexer="tg",
                magnet=magnet,
                leechers=0,
            )
        )
        if len(results) >= limit:
            break

    results.sort(key=lambda r: (-r.quality.score, -r.seeders))
    out = results[:limit]
    if verbose:
        typer.echo(f"[verbose] TorrentGalaxy: {len(out)} resultado(s) exibidos.")
    return out


def _search_scrape_generic(
    base_url: str,
    search_url: str,
    query: str,
    limit: int,
    indexer: str,
    use_video: bool,
    allowed: set[str] | None,
    no_quality_filter: bool,
    verbose: bool,
    magnet_re: str = r'href="(magnet:\?xt=[^"]+)"',
    title_in_quote: str = r'title="((?:[^"\\]|\\.)*)"',
    seeders_re: str | None = None,
    size_re: str | None = None,
) -> list[SearchResult]:
    """Helper: GET search_url, extrai magnets e títulos por regex, retorna SearchResult."""
    import re
    import urllib.parse

    import requests

    results: list[SearchResult] = []
    try:
        resp = requests.get(search_url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"})
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        if verbose:
            typer.echo(f"[verbose] Erro {indexer}: {type(e).__name__}: {e}")
        return []

    magnet_pat = re.compile(magnet_re, re.I)
    title_pat = re.compile(title_in_quote, re.I)

    def clean(t: str) -> str:
        t = re.sub(r"<[^>]+>", "", t)
        t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
        return t.strip() or ""

    for m in magnet_pat.finditer(html):
        magnet = m.group(1)
        before = html[: m.start()]
        titles_before = title_pat.findall(before)
        title = clean(titles_before[-1]) if titles_before else "Torrent"
        if len(title) < 3 or title.lower() in ("torrent", "download", "magnet", "get"):
            continue
        if use_video:
            quality = parse_quality_video(title)
            if not no_quality_filter and not matches_format_video(quality, allowed):
                continue
        else:
            quality = parse_quality(title)
            if not no_quality_filter and not matches_format(quality, allowed):
                continue
        seeders = 0
        size = ""
        if seeders_re:
            se_m = re.search(seeders_re, before[-500:] if len(before) > 500 else before)
            if se_m:
                try:
                    seeders = int(se_m.group(1).replace(",", ""))
                except (ValueError, IndexError):
                    pass
        results.append(
            SearchResult(
                title=title,
                quality=quality,
                seeders=seeders,
                size=size,
                torrent_id=magnet[:80] or "",
                indexer=indexer,
                magnet=magnet,
                leechers=0,
            )
        )
        if len(results) >= limit:
            break
    results.sort(key=lambda r: (-r.quality.score, -r.seeders))
    return results[:limit]


def search_yts(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no YTS (filmes). Só retorna resultados para content_type=movies."""
    if content_type != "movies":
        return []
    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    s = settings or get_settings()
    base = (getattr(s, "yts_base_url", "") or "https://yts.mx").strip().rstrip("/")
    import urllib.parse

    import requests

    url = f"{base}/api/v2/list_movies.json?query_term={urllib.parse.quote_plus(query)}&limit={min(limit, 50)}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "dl-torrent/1.0"})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        if verbose:
            typer.echo(f"[verbose] Erro YTS: {type(e).__name__}: {e}")
        return []

    movies = data.get("data", {}).get("movies") or []
    results: list[SearchResult] = []
    for mov in movies:
        title = (mov.get("title") or "") + " " + (mov.get("title_long") or "")
        title = title.strip() or mov.get("slug", "")
        if use_video:
            quality = parse_quality_video(title)
            if not no_quality_filter and not matches_format_video(quality, allowed):
                continue
        torrents = mov.get("torrents") or []
        for t in torrents:
            magnet = t.get("url") or ""
            if not magnet.startswith("magnet:"):
                continue
            q_label = (t.get("quality") or "") + " " + (t.get("type") or "")
            seeders = int(t.get("seeds") or 0)
            size = t.get("size", "") or ""
            results.append(
                SearchResult(
                    title=f"{mov.get('title', '')} [{q_label.strip()}]",
                    quality=parse_quality_video(q_label + " " + title),
                    seeders=seeders,
                    size=size,
                    torrent_id=magnet[:80],
                    indexer="yts",
                    magnet=magnet,
                    leechers=int(t.get("peers") or 0),
                )
            )
        if len(results) >= limit:
            break
    results.sort(key=lambda r: (-r.seeders, -r.quality.score))
    out = results[:limit]
    if verbose:
        typer.echo(f"[verbose] YTS: {len(out)} resultado(s).")
    return out


def search_eztv(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no EZTV (séries TV)."""
    if content_type != "tv":
        return []
    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    s = settings or get_settings()
    base = (getattr(s, "eztv_base_url", "") or "https://eztv.re").strip().rstrip("/")
    import urllib.parse

    import requests

    url = f"{base}/search/{urllib.parse.quote_plus(query)}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"})
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        if verbose:
            typer.echo(f"[verbose] Erro EZTV: {type(e).__name__}: {e}")
        return []

    import re

    magnet_re = re.compile(r'href="(magnet:\?xt=[^"]+)"', re.I)
    results: list[SearchResult] = []
    for m in magnet_re.finditer(html):
        magnet = m.group(1)
        before = html[: m.start()]
        title_m = re.search(r'class="epinfo">([^<]+)<', before[-800:] if len(before) > 800 else before)
        title = (title_m.group(1).strip() if title_m else "Episode").replace("&amp;", "&")
        if len(title) < 2:
            continue
        quality = parse_quality_video(title)
        if not no_quality_filter and not matches_format_video(quality, allowed):
            continue
        results.append(
            SearchResult(
                title=title,
                quality=quality,
                seeders=0,
                size="",
                torrent_id=magnet[:80],
                indexer="eztv",
                magnet=magnet,
                leechers=0,
            )
        )
        if len(results) >= limit:
            break
    results.sort(key=lambda r: (-r.quality.score, -r.seeders))
    if verbose:
        typer.echo(f"[verbose] EZTV: {len(results[:limit])} resultado(s).")
    return results[:limit]


def search_nyaa(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no NYAA (anime)."""
    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    s = settings or get_settings()
    base = (getattr(s, "nyaa_base_url", "") or "https://nyaa.si").strip().rstrip("/")
    import urllib.parse

    import requests

    url = f"{base}/?f=0&c=0_0&q={urllib.parse.quote_plus(query)}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"})
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        if verbose:
            typer.echo(f"[verbose] Erro NYAA: {type(e).__name__}: {e}")
        return []

    import re

    results: list[SearchResult] = []
    for row in re.finditer(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL):
        block = row.group(1)
        href = re.search(r'href="(magnet:\?xt=[^"]+)"', block)
        if not href:
            continue
        magnet = href.group(1)
        cells = re.findall(r'<td[^>]*>([^<]*(?:<[^/][^>]*>[^<]*)*)</td>', block)
        title_cell = re.search(r'title="([^"]+)"', block) or (re.search(r'>(.*?)</a>', block) if cells else None)
        title = ""
        if title_cell:
            title = title_cell.group(1).replace("&amp;", "&").strip()
        if len(cells) >= 4:
            size = re.sub(r"<[^>]+>", "", cells[3]).strip() if len(cells) > 3 else ""
            seeders_s = re.sub(r"<[^>]+>", "", cells[5]).strip() if len(cells) > 5 else "0"
            try:
                seeders = int(seeders_s)
            except ValueError:
                seeders = 0
        else:
            size = ""
            seeders = 0
        if not title:
            title = "Torrent"
        quality = parse_quality_video(title) if use_video else parse_quality(title)
        if not no_quality_filter and (use_video and not matches_format_video(quality, allowed) or not use_video and not matches_format(quality, allowed)):
            continue
        results.append(
            SearchResult(
                title=title,
                quality=quality,
                seeders=seeders,
                size=size,
                torrent_id=magnet[:80],
                indexer="nyaa",
                magnet=magnet,
                leechers=0,
            )
        )
        if len(results) >= limit:
            break
    results.sort(key=lambda r: (-r.seeders, -r.quality.score))
    if verbose:
        typer.echo(f"[verbose] NYAA: {len(results[:limit])} resultado(s).")
    return results[:limit]


def search_limetorrents(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no Limetorrents."""
    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    s = settings or get_settings()
    base = (getattr(s, "limetorrents_base_url", "") or "https://www.limetorrents.lol").strip().rstrip("/")
    import urllib.parse

    search_path = f"/search/all/{urllib.parse.quote_plus(query)}/seeds/1/"
    url = base + search_path
    out = _search_scrape_generic(
        base_url=base,
        search_url=url,
        query=query,
        limit=limit,
        indexer="limetorrents",
        use_video=use_video,
        allowed=allowed,
        no_quality_filter=no_quality_filter,
        verbose=verbose,
    )
    if verbose and out:
        typer.echo(f"[verbose] Limetorrents: {len(out)} resultado(s).")
    return out


def search_torlock(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no Torlock."""
    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    s = settings or get_settings()
    base = (getattr(s, "torlock_base_url", "") or "https://www.torlock.com").strip().rstrip("/")
    import urllib.parse

    url = f"{base}/all/torrents/{urllib.parse.quote_plus(query)}.html"
    out = _search_scrape_generic(
        base_url=base,
        search_url=url,
        query=query,
        limit=limit,
        indexer="torlock",
        use_video=use_video,
        allowed=allowed,
        no_quality_filter=no_quality_filter,
        verbose=verbose,
    )
    if verbose and out:
        typer.echo(f"[verbose] Torlock: {len(out)} resultado(s).")
    return out


def search_speedtorrent(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no SpeedTorrent."""
    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    s = settings or get_settings()
    base = (getattr(s, "speedtorrent_base_url", "") or "https://www.speedtorrent.re").strip().rstrip("/")
    import urllib.parse

    url = f"{base}/search/all/{urllib.parse.quote_plus(query)}/seeds/1/"
    out = _search_scrape_generic(
        base_url=base,
        search_url=url,
        query=query,
        limit=limit,
        indexer="speedtorrent",
        use_video=use_video,
        allowed=allowed,
        no_quality_filter=no_quality_filter,
        verbose=verbose,
    )
    if verbose and out:
        typer.echo(f"[verbose] SpeedTorrent: {len(out)} resultado(s).")
    return out


def search_fitgirl(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no FitGirl Repacks (repacks de jogos). Retorna resultados como vídeo/genérico."""
    use_video = True
    allowed = None if no_quality_filter else (parse_format_filter_video(format_filter) if content_type in ("movies", "tv") else None)
    s = settings or get_settings()
    base = (getattr(s, "fitgirl_base_url", "") or "https://fitgirl-repacks.site").strip().rstrip("/")
    import re
    import urllib.parse

    import requests

    url = f"{base}/?s={urllib.parse.quote_plus(query)}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"})
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        if verbose:
            typer.echo(f"[verbose] Erro FitGirl: {type(e).__name__}: {e}")
        return []

    results: list[SearchResult] = []
    for m in re.finditer(r'<a[^>]+href="(magnet:\?xt=[^"]+)"[^>]*>', html, re.I):
        magnet = m.group(1)
        before = html[: m.start()]
        title_m = re.search(r'<a[^>]+href="[^"]*"[^>]*>([^<]+)</a>', before[-2000:] if len(before) > 2000 else before)
        title = (title_m.group(1).strip() if title_m else "Repack").replace("&amp;", "&")
        if len(title) < 3:
            continue
        quality = parse_quality_video(title)
        if not no_quality_filter and not matches_format_video(quality, allowed):
            continue
        results.append(
            SearchResult(
                title=title,
                quality=quality,
                seeders=0,
                size="",
                torrent_id=magnet[:80],
                indexer="fitgirl",
                magnet=magnet,
                leechers=0,
            )
        )
        if len(results) >= limit:
            break
    results.sort(key=lambda r: (-r.quality.score, -r.seeders))
    if verbose and results:
        typer.echo(f"[verbose] FitGirl: {len(results[:limit])} resultado(s).")
    return results[:limit]


def search_rutracker(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """Busca no RuTracker. Magnet pode exigir login em alguns tópicos."""
    use_video, allowed = _quality_filter_for_content_type(content_type, format_filter, no_quality_filter)
    s = settings or get_settings()
    base = (getattr(s, "rutracker_base_url", "") or "https://rutracker.org").strip().rstrip("/")
    import re
    import urllib.parse

    import requests

    url = f"{base}/forum/tracker.php?nm={urllib.parse.quote_plus(query)}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"})
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        if verbose:
            typer.echo(f"[verbose] Erro RuTracker: {type(e).__name__}: {e}")
        return []

    results: list[SearchResult] = []
    for m in re.finditer(r'href="(magnet:\?xt=[^"]+)"', html, re.I):
        magnet = m.group(1)
        before = html[: m.start()]
        title_m = re.search(r'class="topictitle"[^>]*>([^<]+)<', before[-1500:] if len(before) > 1500 else before)
        title = (title_m.group(1).strip() if title_m else "Torrent").replace("&amp;", "&")
        if len(title) < 2:
            continue
        quality = parse_quality_video(title) if use_video else parse_quality(title)
        if not no_quality_filter and (use_video and not matches_format_video(quality, allowed) or not use_video and not matches_format(quality, allowed)):
            continue
        results.append(
            SearchResult(
                title=title,
                quality=quality,
                seeders=0,
                size="",
                torrent_id=magnet[:80],
                indexer="rutracker",
                magnet=magnet,
                leechers=0,
            )
        )
        if len(results) >= limit:
            break
    results.sort(key=lambda r: (-r.quality.score, -r.seeders))
    if verbose and results:
        typer.echo(f"[verbose] RuTracker: {len(results[:limit])} resultado(s).")
    return results[:limit]


def search_iptorrents(
    query: str,
    limit: int = 50,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    settings=None,
) -> list[SearchResult]:
    """IPTorrents é tracker privado; requer cookie de sessão. Por ora retorna vazio."""
    if verbose:
        typer.echo("[verbose] IPTorrents: tracker privado (não implementado sem auth).")
    return []


def get_magnet_for_result(result: SearchResult) -> str | None:
    """Obtém o magnet para um resultado (usa result.magnet se já veio da busca, senão 1337x)."""
    if result.magnet:
        return result.magnet
    if result.indexer == "1337x":
        return get_magnet_1337x(result.torrent_id)
    if result.indexer in ("tpb", "tg", "yts", "eztv", "nyaa", "limetorrents", "torlock", "speedtorrent", "fitgirl", "rutracker"):
        return result.magnet
    return None


def _format_choice(result: SearchResult, i: int) -> str:
    """Uma linha para exibir na lista de checkboxes."""
    title_short = (result.title[:60] + "…") if len(result.title) > 60 else result.title
    idx_tag = f"[{result.indexer.upper()}] " if result.indexer else ""
    return f"{idx_tag}[{result.quality.label}] {result.seeders} seed | {result.size} — {title_short}"


def _print_results_list(
    results: list[SearchResult],
    page: int = 1,
    page_size: int | None = None,
    total_pages: int = 1,
) -> None:
    """Exibe a lista numerada de resultados (uma página se page_size for informado)."""
    typer.echo("")
    if page_size is not None and total_pages > 1:
        typer.echo(f"  Página {page}/{total_pages} ({len(results)} itens nesta página)")
        typer.echo("")
    for i, r in enumerate(results, 1):
        idx_tag = f"[{r.indexer.upper()}] " if r.indexer else ""
        se_le = f"{r.seeders} seed | {r.leechers} leech"
        typer.echo(f"  {i}. {idx_tag}[{r.quality.label}] {se_le} | {r.size}")
        typer.echo(f"     {r.title[:72]}{'…' if len(r.title) > 72 else ''}")
    typer.echo("")


def search_all(
    query: str,
    limit: int = 1000,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    indexers: list[str] | None = None,
    settings=None,
    sort_by: str = "seeders",
) -> list[SearchResult]:
    """Busca em todos os indexadores solicitados, junta e ordena (por seeders/leechers ou tamanho)."""
    if not indexers:
        indexers = list(DEFAULT_INDEXERS)
    indexers = [x.strip().lower() for x in indexers if x.strip()]
    indexers = [x for x in indexers if x in ALL_INDEXERS]
    if not indexers:
        indexers = list(DEFAULT_INDEXERS)
    all_results: list[SearchResult] = []
    # Buscar mais para permitir limite alto (cada indexador retorna até fetch_limit*2)
    fetch_limit = max(limit, 100)

    if "1337x" in indexers:
        r1337 = search_1337x(
            query,
            limit=fetch_limit * 2,
            format_filter=format_filter,
            no_quality_filter=no_quality_filter,
            verbose=verbose,
            music_category_only=music_category_only,
            content_type=content_type,
        )
        all_results.extend(r1337)

    if "tpb" in indexers:
        rtpb = search_tpb(
            query,
            limit=fetch_limit * 2,
            format_filter=format_filter,
            no_quality_filter=no_quality_filter,
            verbose=verbose,
            music_category_only=music_category_only,
            content_type=content_type,
            settings=settings,
        )
        all_results.extend(rtpb)
        if not rtpb and not verbose:
            typer.echo("  TPB: nenhum resultado (espelho pode estar indisponível; use -V para detalhes).", err=True)

    if "tg" in indexers:
        rtg = search_tg(
            query,
            limit=fetch_limit * 2,
            format_filter=format_filter,
            no_quality_filter=no_quality_filter,
            verbose=verbose,
            music_category_only=music_category_only,
            content_type=content_type,
            settings=settings,
        )
        all_results.extend(rtg)

    if "yts" in indexers:
        all_results.extend(
            search_yts(
                query,
                limit=fetch_limit * 2,
                format_filter=format_filter,
                no_quality_filter=no_quality_filter,
                verbose=verbose,
                music_category_only=music_category_only,
                content_type=content_type,
                settings=settings,
            )
        )
    if "eztv" in indexers:
        all_results.extend(
            search_eztv(
                query,
                limit=fetch_limit * 2,
                format_filter=format_filter,
                no_quality_filter=no_quality_filter,
                verbose=verbose,
                music_category_only=music_category_only,
                content_type=content_type,
                settings=settings,
            )
        )
    if "nyaa" in indexers:
        all_results.extend(
            search_nyaa(
                query,
                limit=fetch_limit * 2,
                format_filter=format_filter,
                no_quality_filter=no_quality_filter,
                verbose=verbose,
                music_category_only=music_category_only,
                content_type=content_type,
                settings=settings,
            )
        )
    if "limetorrents" in indexers:
        all_results.extend(
            search_limetorrents(
                query,
                limit=fetch_limit * 2,
                format_filter=format_filter,
                no_quality_filter=no_quality_filter,
                verbose=verbose,
                music_category_only=music_category_only,
                content_type=content_type,
                settings=settings,
            )
        )
    if "torlock" in indexers:
        all_results.extend(
            search_torlock(
                query,
                limit=fetch_limit * 2,
                format_filter=format_filter,
                no_quality_filter=no_quality_filter,
                verbose=verbose,
                music_category_only=music_category_only,
                content_type=content_type,
                settings=settings,
            )
        )
    if "speedtorrent" in indexers:
        all_results.extend(
            search_speedtorrent(
                query,
                limit=fetch_limit * 2,
                format_filter=format_filter,
                no_quality_filter=no_quality_filter,
                verbose=verbose,
                music_category_only=music_category_only,
                content_type=content_type,
                settings=settings,
            )
        )
    if "fitgirl" in indexers:
        all_results.extend(
            search_fitgirl(
                query,
                limit=fetch_limit * 2,
                format_filter=format_filter,
                no_quality_filter=no_quality_filter,
                verbose=verbose,
                music_category_only=music_category_only,
                content_type=content_type,
                settings=settings,
            )
        )
    if "rutracker" in indexers:
        all_results.extend(
            search_rutracker(
                query,
                limit=fetch_limit * 2,
                format_filter=format_filter,
                no_quality_filter=no_quality_filter,
                verbose=verbose,
                music_category_only=music_category_only,
                content_type=content_type,
                settings=settings,
            )
        )
    if "iptorrents" in indexers:
        all_results.extend(
            search_iptorrents(
                query,
                limit=fetch_limit * 2,
                format_filter=format_filter,
                no_quality_filter=no_quality_filter,
                verbose=verbose,
                music_category_only=music_category_only,
                content_type=content_type,
                settings=settings,
            )
        )

    if sort_by == "size":
        all_results.sort(
            key=lambda r: (-_parse_size_to_bytes(r.size), -r.quality.score, -r.seeders)
        )
    else:
        # seeders (default): ordenar por Se/Le depois qualidade
        all_results.sort(
            key=lambda r: (-r.seeders, -r.leechers, -r.quality.score)
        )
    return all_results[:limit]


def select_indices(
    results: list[SearchResult],
    *,
    best: bool = False,
    index: int | None = None,
    auto_download_best_result: bool = False,
    verbose: bool = False,
    page_size: int | None = 20,
) -> list[int] | None:
    """
    Seleção de índices pelo usuário (--best, --index, ou navegação paginada n/p + números).
    Com page_size, exibe 20 itens por página; n=próxima, p=anterior, números=selecionar.
    Retorna lista de índices globais ou None se cancelado.
    """
    if auto_download_best_result or best:
        return [0]
    if index is not None:
        if 1 <= index <= len(results):
            return [index - 1]
        typer.echo(f"Índice inválido. Use 1 a {len(results)}.")
        raise typer.Exit(1)
    psize = page_size or 20
    total_pages = max(1, (len(results) + psize - 1) // psize)
    page = 1

    def show_page() -> None:
        start = (page - 1) * psize
        slice_results = results[start : start + psize]
        _print_results_list(slice_results, page=page, page_size=psize, total_pages=total_pages)
        if total_pages > 1:
            typer.echo("  n = próxima página   p = página anterior")
        typer.echo("  Digite os números dos itens (ex: 1,3,5) para selecionar ou 0 para cancelar.")

    while True:
        try:
            show_page()
            raw = input("Números: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            typer.echo("Cancelado.")
            return None
        if not raw:
            continue
        if raw in ("n", "next", "próxima", "proxima"):
            if page < total_pages:
                page += 1
            continue
        if raw in ("p", "prev", "anterior"):
            if page > 1:
                page -= 1
            continue
        if raw == "0":
            typer.echo("Cancelado.")
            return None
        try:
            local_indices = [int(x.strip()) - 1 for x in raw.split(",") if x.strip()]
        except ValueError:
            typer.echo("Use apenas números separados por vírgula (ex: 1,3,5) ou 0 para cancelar.")
            continue
        start = (page - 1) * psize
        max_local = min(psize, len(results) - start) - 1
        local_indices = [i for i in local_indices if 0 <= i <= max_local]
        if not local_indices:
            typer.echo(f"Nenhum item válido. Use 1 a {min(psize, len(results) - start)} nesta página.")
            continue
        global_indices = sorted(set(start + i for i in local_indices))
        return global_indices


def send_selected_to_destination(
    results: list[SearchResult],
    selected_indices: list[int],
    *,
    save_to_watch_folder: bool = False,
    watch_folder_path: str | None = None,
    download_direct: bool = False,
    download_direct_path: str | None = None,
    download_direct_port: int | None = None,
    download_background: bool = False,
    organize_by_artist_album: bool = False,
    content_type: ContentType = "music",
    settings=None,
) -> dict:
    """Envia os resultados selecionados ao destino (watch folder, cliente, fila, download direto).
    Retorna dict com: ok, fail, errors (list[str]), added_titles (list[str]), destination.
    Levanta RuntimeError se não for possível resolver o destino.
    """
    destination = resolve_destination(
        save_to_watch_folder=save_to_watch_folder,
        watch_folder_path=watch_folder_path,
        download_direct=download_direct,
        download_direct_path=download_direct_path,
        download_direct_port=download_direct_port,
        download_background=download_background,
        organize_by_artist_album=organize_by_artist_album,
        content_type=content_type,
        settings=settings,
    )
    ok, fail = 0, 0
    errors: list[str] = []
    added_titles: list[str] = []
    for i in selected_indices:
        if i < 0 or i >= len(results):
            continue
        result = results[i]
        magnet = get_magnet_for_result(result)
        if not magnet:
            fail += 1
            errors.append(f"Não foi possível obter magnet: {result.title[:50]}…")
            continue
        success, err = destination.send(magnet, result.title)
        if success:
            ok += 1
            added_titles.append(result.title)
        else:
            fail += 1
            errors.append(err or f"Erro ao adicionar: {result.title[:50]}…")
    return {"ok": ok, "fail": fail, "errors": errors, "added_titles": added_titles, "destination": destination}


def run_search(
    query: str,
    album: str | None = None,
    best: bool = False,
    index: int | None = None,
    limit: int = 200,
    format_filter: str | None = None,
    no_quality_filter: bool = False,
    verbose: bool = False,
    music_category_only: bool = True,
    content_type: ContentType = "music",
    auto_download_best_result: bool = False,
    save_to_watch_folder: bool = False,
    watch_folder_path: str | None = None,
    download_direct: bool = False,
    download_direct_path: str | None = None,
    download_direct_port: int | None = None,
    download_background: bool = False,
    organize_by_artist_album: bool = False,
    indexers: list[str] | None = None,
    settings=None,
    sort_by: str = "seeders",
    page_size: int = 20,
) -> None:
    """Buscar torrents, exibir lista paginada (n/p navegar) e baixar os selecionados.
    settings: injetável para testes (DIP); None usa get_settings().
    sort_by: seeders (Se/Le) ou size (tamanho). page_size: itens por página (20).
    """
    full_query = f"{query} {album or ''}".strip()
    try:
        from .db import history_add_query
        history_add_query(full_query)
    except Exception:
        pass  # não falhar a busca por falha no histórico

    results = search_all(
        full_query,
        limit=limit,
        format_filter=format_filter,
        no_quality_filter=no_quality_filter,
        verbose=verbose,
        music_category_only=music_category_only,
        content_type=content_type,
        indexers=indexers,
        settings=settings,
        sort_by=sort_by,
    )

    if not results:
        if no_quality_filter:
            typer.echo("Nenhum resultado encontrado.")
        else:
            msg = "Nenhum resultado aceitável"
            if format_filter:
                msg += f" para formato(s): {format_filter}"
            else:
                msg += " (FLAC/ALAC/MP3 320/MP3 até 198 kbps)"
            msg += "."
            typer.echo(msg)
        raise typer.Exit(1)

    selected_indices = select_indices(
        results,
        best=best,
        index=index,
        auto_download_best_result=auto_download_best_result,
        verbose=verbose,
        page_size=page_size,
    )
    if selected_indices is None or not selected_indices:
        if selected_indices is not None:
            typer.echo("Nenhum item selecionado.")
        return

    try:
        out = send_selected_to_destination(
            results,
            selected_indices,
            save_to_watch_folder=save_to_watch_folder,
            watch_folder_path=watch_folder_path,
            download_direct=download_direct,
            download_direct_path=download_direct_path,
            download_direct_port=download_direct_port,
            download_background=download_background,
            organize_by_artist_album=organize_by_artist_album,
            content_type=content_type,
            settings=settings,
        )
    except RuntimeError as e:
        typer.echo(str(e))
        raise typer.Exit(1)

    ok, fail = out["ok"], out["fail"]
    errors = out.get("errors", [])
    added_titles = out.get("added_titles", [])
    destination = out.get("destination")

    for title in added_titles:
        typer.echo(f"  ✓ Adicionado: {title[:55]}…")
    for err in errors:
        typer.echo(f"  ✗ {err}")
    if ok and destination:
        def _progress(pct: float, done: int, total: int) -> None:
            typer.echo(f"\r  Download: {pct * 100:.1f}% ({done}/{total} concluídos)  ", nl=False)
        destination.run_after_if_sync(progress_callback=_progress)
        typer.echo(destination.success_message(ok, fail))
    elif fail > 0 and not ok:
        if destination:
            typer.echo(destination.failure_message())
        raise typer.Exit(1)
