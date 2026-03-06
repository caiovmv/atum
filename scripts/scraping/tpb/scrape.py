"""
Scraping The Pirate Bay. Magnet na listagem.
Env: TPB_BASE_URL (default: https://tpb.party)
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
    clean_html_title,
)

DEFAULT_BASE = "https://tpb.party"


def _search_url(base: str, query: str) -> str:
    # tpb.party e espelhos: /search/query/page/order/category (order 7 = seeders, category 0 = all)
    return f"{base}/search/{urllib.parse.quote_plus(query)}/1/7/0"


def scrape(query: str, limit: int = 25) -> list[dict]:
    base = env_base_url("TPB_BASE_URL", DEFAULT_BASE)
    url = _search_url(base, query)
    try:
        html = get_url(url)
    except RuntimeError:
        raise
    except Exception:
        return []
    # TPB: linhas de resultado têm .detName com título e magnet
    magnet_re = re.compile(r'href="(magnet:\?xt=[^"]+)"', re.I)
    # Título: link com class detLink ou texto antes do magnet na mesma linha
    title_re = re.compile(r'class="detLink"[^>]*>([^<]+)<', re.I)
    results: list[dict] = []
    seen: set[str] = set()
    for m in magnet_re.finditer(html):
        magnet = m.group(1)
        if magnet in seen:
            continue
        seen.add(magnet)
        before = html[: m.start()]
        titles = title_re.findall(before)
        title = clean_html_title(titles[-1]) if titles else ""
        if not title or len(title) < 2 or title.lower() == "torrent":
            # Fallback: título no parâmetro dn= do magnet
            try:
                parsed = urllib.parse.urlparse(magnet)
                qs = urllib.parse.parse_qs(parsed.query)
                dn = (qs.get("dn") or [""])[0]
                if dn:
                    title = urllib.parse.unquote_plus(dn).strip()[:200]
            except Exception:
                pass
        if not title or len(title) < 2:
            title = "Torrent"
        # Tamanho/seeders: procurar na mesma região (td)
        size = ""
        seeders = 0
        block = before[-1500:] if len(before) > 1500 else before
        size_m = re.search(r"(\d+\.?\d*\s*[KMGT]?i?B)", block, re.I)
        if size_m:
            size = size_m.group(1).strip()
        seed_m = re.findall(r"<td[^>]*>(\d+)</td>", block)
        if len(seed_m) >= 2:
            try:
                seeders = int(seed_m[-2])
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
    main_usage("tpb", DEFAULT_BASE, "TPB_BASE_URL")
    query = sys.argv[1]
    json_out = "--no-json" not in sys.argv
    results = scrape(query, limit=25)
    output_results(results, json_output=json_out)


if __name__ == "__main__":
    main()
