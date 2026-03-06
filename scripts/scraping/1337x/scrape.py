"""
Scraping 1337x (ou espelho 1377x). Magnet via pagina de detalhe.
Env: X1337_BASE_URL (default: https://www.1377x.to)
"""
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.scraping._common import (
    env_base_url,
    get_url,
    main_usage,
    output_results,
    clean_html_title,
)

DEFAULT_BASE = "https://www.1377x.to"


def _search_url(base: str, query: str, page: int = 1) -> str:
    return f"{base}/search/{urllib.parse.quote_plus(query)}/{page}/"


def _detail_url(base: str, path: str) -> str:
    if path.startswith("http"):
        return path
    return base.rstrip("/") + ("/" + path.lstrip("/") if path else "")


def scrape(query: str, limit: int = 20) -> list[dict]:
    base = env_base_url("X1337_BASE_URL", DEFAULT_BASE)
    results: list[dict] = []
    seen_magnets: set[str] = set()
    page = 1
    while len(results) < limit and page <= 3:
        url = _search_url(base, query, page)
        try:
            html = get_url(url)
        except RuntimeError:
            raise
        except Exception:
            break
        row_re = re.compile(r'<a\s+href="(/torrent/[^"]+)"[^>]*>([^<]+)</a>', re.I)
        magnet_re = re.compile(r'href="(magnet:\?xt=[^"]+)"', re.I)
        for m in row_re.finditer(html):
            path, raw_title = m.group(1), m.group(2)
            title = clean_html_title(raw_title)
            if not title or len(title) < 2 or title.lower() in ("torrent", "download", "home", "search"):
                continue
            start = max(0, m.start() - 200)
            end = min(len(html), m.end() + 800)
            block = html[start:end]
            mag_m = magnet_re.search(block)
            magnet = mag_m.group(1) if mag_m else None
            if not magnet:
                try:
                    detail_html = get_url(_detail_url(base, path))
                    mag_m2 = magnet_re.search(detail_html)
                    magnet = mag_m2.group(1) if mag_m2 else None
                except RuntimeError:
                    raise
                except Exception:
                    pass
            if magnet and magnet not in seen_magnets:
                seen_magnets.add(magnet)
                results.append({"title": title, "magnet": magnet, "torrent_url": None, "seeders": 0, "size": ""})
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break
        page += 1
    return results[:limit]


def main() -> None:
    main_usage("1337x", DEFAULT_BASE, "X1337_BASE_URL")
    query = sys.argv[1]
    json_out = "--no-json" not in sys.argv
    results = scrape(query, limit=25)
    output_results(results, json_output=json_out)


if __name__ == "__main__":
    main()
