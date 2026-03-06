# Limetorrents. Env: LIMETORRENTS_BASE_URL
# Listagem tem links para *-torrent-ID.html; magnet está na página de detalhe
import re
import sys
import urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.scraping._common import env_base_url, get_url, main_usage, output_results, clean_html_title
DEFAULT_BASE = "https://www.limetorrents.lol"

def _search_url(base, query):
    return f"{base}/search/all/{urllib.parse.quote_plus(query)}/seeds/1/"

def scrape(query, limit=25):
    base = env_base_url("LIMETORRENTS_BASE_URL", DEFAULT_BASE).rstrip("/")
    try:
        html = get_url(_search_url(base, query))
    except RuntimeError:
        raise
    except Exception:
        return []
    magnet_re = re.compile(r'href="(magnet:\?xt=[^"]+)"', re.I)
    title_re = re.compile(r'title="((?:[^"\\]|\\.)*)"', re.I)
    results, seen = [], set()
    for m in magnet_re.finditer(html):
        magnet = m.group(1)
        if magnet in seen:
            continue
        seen.add(magnet)
        before = html[: m.start()]
        titles = title_re.findall(before)
        title = clean_html_title(titles[-1]) if titles else ""
        if not title or len(title) < 3 or title.lower() in ("torrent", "download", "magnet", "get"):
            try:
                parsed = urllib.parse.urlparse(magnet)
                qs = urllib.parse.parse_qs(parsed.query)
                dn = (qs.get("dn") or [""])[0]
                if dn:
                    title = urllib.parse.unquote_plus(dn).strip()[:200]
            except Exception:
                pass
        if not title:
            title = "Torrent"
        results.append({"title": title, "magnet": magnet, "torrent_url": None, "seeders": 0, "size": ""})
        if len(results) >= limit:
            return results[:limit]
    # Magnet não na listagem; seguir links *-torrent-ID.html
    detail_re = re.compile(r'href="([^"]*-torrent-(\d+)\.html)"', re.I)
    seen_ids = set()
    detail_links = []
    for m in detail_re.finditer(html):
        path, tid = m.group(1), m.group(2)
        if tid not in seen_ids:
            seen_ids.add(tid)
            full_url = path if path.startswith("http") else (base + "/" + path.lstrip("/"))
            detail_links.append(full_url)
    for detail_url in detail_links[:limit]:
        if len(results) >= limit:
            break
        try:
            ep_html = get_url(detail_url)
            mag_m = magnet_re.search(ep_html)
            if not mag_m:
                continue
            magnet = mag_m.group(1)
            if magnet in seen:
                continue
            seen.add(magnet)
            before = ep_html[: mag_m.start()]
            titles = title_re.findall(before)
            title = clean_html_title(titles[-1]) if titles else ""
            if not title or len(title) < 2:
                try:
                    parsed = urllib.parse.urlparse(magnet)
                    qs = urllib.parse.parse_qs(parsed.query)
                    dn = (qs.get("dn") or [""])[0]
                    if dn:
                        title = urllib.parse.unquote_plus(dn).strip()[:200]
                except Exception:
                    pass
            if not title:
                title = "Torrent"
            results.append({"title": title, "magnet": magnet, "torrent_url": None, "seeders": 0, "size": ""})
        except (RuntimeError, Exception):
            continue
    return results[:limit]

def main():
    main_usage("limetorrents", DEFAULT_BASE, "LIMETORRENTS_BASE_URL")
    query = sys.argv[1]
    output_results(scrape(query, 25), json_output="--no-json" not in sys.argv)

if __name__ == "__main__":
    main()
