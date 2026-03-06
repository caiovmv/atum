"""
Scraping EZTV (series). Magnet + titulo em class="epinfo".
Env: EZTV_BASE_URL (default: https://eztv.re)
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
)

DEFAULT_BASE = "https://eztv.re"


def _search_url(base: str, query: str) -> str:
    return f"{base}/search/{urllib.parse.quote_plus(query)}"


def scrape(query: str, limit: int = 25) -> list[dict]:
    base = env_base_url("EZTV_BASE_URL", DEFAULT_BASE).rstrip("/")
    url = _search_url(base, query)
    try:
        html = get_url(url)
    except RuntimeError:
        raise
    except Exception:
        return []
    magnet_re = re.compile(r'href="(magnet:\?xt=[^"]+)"', re.I)
    title_re = re.compile(r'class="epinfo">([^<]+)<', re.I)
    title_ep_re = re.compile(r'<a[^>]+href="[^"]*ep/\d+[^"]*"[^>]*>([^<]+)</a>', re.I)
    results: list[dict] = []
    seen: set[str] = set()
    for m in magnet_re.finditer(html):
        magnet = m.group(1)
        if magnet in seen:
            continue
        seen.add(magnet)
        before = html[: m.start()]
        block = before[-2000:] if len(before) > 2000 else before
        title_m = title_re.search(block)
        if title_m:
            title = title_m.group(1).strip().replace("&amp;", "&")
        else:
            titles_ep = title_ep_re.findall(block)
            title = (titles_ep[-1].strip().replace("&amp;", "&") if titles_ep else "Episode")
        if len(title) < 2:
            continue
        results.append({"title": title, "magnet": magnet, "torrent_url": None, "seeders": 0, "size": ""})
        if len(results) >= limit:
            return results[:limit]
    # Se a busca não tem magnet na página, seguir links /ep/ e extrair magnet de cada
    if len(results) < limit:
        ep_link_re = re.compile(r'href="(/ep/(\d+)/[^"]*)"', re.I)
        ep_links: list[tuple[str, str]] = []
        seen_ids: set[str] = set()
        for m in ep_link_re.finditer(html):
            path, ep_id = m.group(1), m.group(2)
            if ep_id not in seen_ids:
                seen_ids.add(ep_id)
                ep_links.append((path, ep_id))
        for path, _ in ep_links[:limit]:
            if len(results) >= limit:
                break
            try:
                ep_url = base + path if path.startswith("/") else base + "/" + path
                ep_html = get_url(ep_url)
                mag_m = magnet_re.search(ep_html)
                if not mag_m:
                    continue
                magnet = mag_m.group(1)
                if magnet in seen:
                    continue
                seen.add(magnet)
                before = ep_html[: mag_m.start()]
                block = before[-2000:] if len(before) > 2000 else before
                title_m = title_re.search(ep_html) or title_re.search(block)
                if title_m:
                    title = title_m.group(1).strip().replace("&amp;", "&")
                else:
                    titles_ep = title_ep_re.findall(ep_html)
                    title = (titles_ep[-1].strip().replace("&amp;", "&") if titles_ep else "Episode")
                if len(title) < 2:
                    title = "Episode"
                results.append({"title": title, "magnet": magnet, "torrent_url": None, "seeders": 0, "size": ""})
            except (RuntimeError, Exception):
                continue
    return results[:limit]


def main() -> None:
    main_usage("eztv", DEFAULT_BASE, "EZTV_BASE_URL")
    query = sys.argv[1]
    json_out = "--no-json" not in sys.argv
    results = scrape(query, limit=25)
    output_results(results, json_output=json_out)


if __name__ == "__main__":
    main()
