"""
Scraping Nyaa (anime). Linhas <tr> com magnet, células para título/tamanho/seeders.
Env: NYAA_BASE_URL (default: https://nyaa.si)
"""
import re
import sys
import urllib.parse

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))

from scripts.scraping._common import (
    env_base_url,
    get_url,
    main_usage,
    output_results,
)

DEFAULT_BASE = "https://nyaa.si"


def _search_url(base: str, query: str) -> str:
    return f"{base}/?f=0&c=0_0&q={urllib.parse.quote_plus(query)}"


def scrape(query: str, limit: int = 25) -> list[dict]:
    base = env_base_url("NYAA_BASE_URL", DEFAULT_BASE)
    url = _search_url(base, query)
    try:
        html = get_url(url)
    except RuntimeError:
        raise
    except Exception:
        return []
    results: list[dict] = []
    # Nyaa: magnet na linha; título no link para /view/ (evitar pegar categoria tipo "Anime - English-translated")
    view_link_text_re = re.compile(r'<a[^>]+href="(?:https?://[^/]*nyaa\.si)?/view/\d+[^"]*"[^>]*>([^<]+)</a>', re.I)
    view_title_attr_re = re.compile(r'<a[^>]+href="(?:https?://[^/]*nyaa\.si)?/view/\d+[^"]*"[^>]*title="([^"]+)"', re.I)
    # Categoria costuma ser curta e no formato "X - Y" (ex.: "Anime - English-translated")
    def _is_category(s: str) -> bool:
        s = s.strip()
        if len(s) > 60:
            return False
        if re.match(r"^[A-Za-z0-9\s]+-\s*[A-Za-z0-9\s\-]+$", s) and len(s) < 40:
            return True
        return False
    for row in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL):
        block = row.group(1)
        href = re.search(r'href="(magnet:\?xt=[^"]+)"', block)
        if not href:
            continue
        magnet = href.group(1)
        cells = re.findall(r"<td[^>]*>([^<]*(?:<[^/][^>]*>[^<]*)*)</td>", block)
        # Preferir texto do link /view/ (nome do torrent); senão title=; evitar categoria
        title = ""
        for m in view_link_text_re.finditer(block):
            t = m.group(1).replace("&amp;", "&").strip()
            if t and len(t) > 3 and not _is_category(t):
                title = t
                break
        if not title:
            for m in view_title_attr_re.finditer(block):
                t = m.group(1).replace("&amp;", "&").strip()
                if t and len(t) > 3 and not _is_category(t):
                    title = t
                    break
        if not title:
            generic = re.search(r'title="([^"]+)"', block)
            title = (generic.group(1).replace("&amp;", "&").strip() if generic else "Torrent")
        if not title or len(title) < 2:
            title = "Torrent"
        size = ""
        seeders = 0
        if len(cells) >= 4:
            size = re.sub(r"<[^>]+>", "", cells[3]).strip() if len(cells) > 3 else ""
            seeders_s = re.sub(r"<[^>]+>", "", cells[5]).strip() if len(cells) > 5 else "0"
            try:
                seeders = int(seeders_s)
            except ValueError:
                pass
        results.append({
            "title": title,
            "magnet": magnet,
            "torrent_url": None,
            "seeders": seeders,
            "size": size,
        })
        if len(results) >= limit:
            break
    return results[:limit]


def main() -> None:
    main_usage("nyaa", DEFAULT_BASE, "NYAA_BASE_URL")
    query = sys.argv[1]
    json_out = "--no-json" not in sys.argv
    results = scrape(query, limit=25)
    output_results(results, json_output=json_out)


if __name__ == "__main__":
    main()
