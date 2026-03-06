# Scraping YTS via API JSON. Env: YTS_BASE_URL
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.scraping._common import env_base_url, get_url, get_url_json, main_usage, output_results

DEFAULT_BASE = "https://yts.lt"


def _search_url(base: str, query: str, limit: int) -> str:
    return f"{base}/api/v2/list_movies.json?query_term={urllib.parse.quote_plus(query)}&limit={min(limit, 50)}"


def scrape(query: str, limit: int = 25) -> list[dict]:
    base = env_base_url("YTS_BASE_URL", DEFAULT_BASE)
    url = _search_url(base, query, limit)
    data = None
    # API JSON normalmente não precisa de FlareSolverr; tentar direto primeiro
    fs_url = os.environ.get("FLARESOLVERR_URL", "").strip()
    if fs_url:
        saved = os.environ.pop("FLARESOLVERR_URL", None)
        try:
            data = get_url_json(url)
        except Exception:
            pass
        if saved is not None:
            os.environ["FLARESOLVERR_URL"] = saved
    if not data or not isinstance(data, dict):
        try:
            data = get_url_json(url)
        except RuntimeError:
            raise
        except Exception:
            pass
    if not data or not isinstance(data, dict):
        try:
            raw = get_url(url)
            raw = (raw or "").strip()
            if raw.startswith("{"):
                data = json.loads(raw)
        except RuntimeError:
            raise
        except Exception:
            return []
    if not data or not isinstance(data, dict):
        return []
    movies = (data.get("data") or {}).get("movies") or []
    results: list[dict] = []
    for mov in movies:
        title_base = (mov.get("title") or "").strip() or (mov.get("slug") or "")
        for t in mov.get("torrents") or []:
            url_or_magnet = (t.get("url") or "").strip()
            info_hash = (t.get("hash") or "").strip()
            magnet = url_or_magnet
            if magnet.startswith("magnet:"):
                pass
            elif info_hash and len(info_hash) == 40:
                magnet = f"magnet:?xt=urn:btih:{info_hash.upper()}"
            elif magnet:
                # yts.lt e espelhos retornam URL de download; extrair hash e montar magnet
                hash_match = re.search(r"/download/([A-Fa-f0-9]{40})", magnet)
                if hash_match:
                    magnet = f"magnet:?xt=urn:btih:{hash_match.group(1).upper()}"
                else:
                    continue
            else:
                continue
            q = (t.get("quality") or "").strip()
            type_ = (t.get("type") or "").strip()
            label = " ".join(x for x in (q, type_) if x).strip()
            title = f"{title_base} [{label}]" if label else title_base
            results.append({
                "title": title,
                "magnet": magnet,
                "torrent_url": None,
                "seeders": int(t.get("seeds") or 0),
                "size": (t.get("size") or "").strip(),
            })
        if len(results) >= limit:
            break
    return results[:limit]


def main() -> None:
    main_usage("yts", DEFAULT_BASE, "YTS_BASE_URL")
    query = sys.argv[1]
    json_out = "--no-json" not in sys.argv
    results = scrape(query, limit=25)
    output_results(results, json_output=json_out)


if __name__ == "__main__":
    main()
