"""
Testa todos os scrapers com 3 buscas: avatar, led zeppelin, fringe.
Uso: na raiz do projeto, com FLARESOLVERR_URL no .env ou ambiente:
  python -m scripts.scraping.run_all_tests
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

QUERIES = ["avatar", "led zeppelin", "fringe"]
SCRAPERS = [
    "1337x",
    "tpb",
    "yts",
    "eztv",
    "nyaa",
    "limetorrents",
]


def load_scraper(name):
    if name == "1337x":
        spec = importlib.util.spec_from_file_location(
            "scrape_1337x", ROOT / "scripts" / "scraping" / "1337x" / "scrape.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.scrape
    mod = importlib.import_module(f"scripts.scraping.{name}.scrape")
    return mod.scrape


def main():
    print("Scrapers:", ", ".join(SCRAPERS), flush=True)
    print("Queries:", QUERIES, flush=True)
    print("-" * 60, flush=True)
    results = {}
    for scraper in SCRAPERS:
        print(f"  Testing {scraper}...", flush=True)
        results[scraper] = {}
        try:
            scrape_fn = load_scraper(scraper)
        except Exception as e:
            for q in QUERIES:
                results[scraper][q] = f"import error: {e}"
            continue
        for query in QUERIES:
            try:
                items = scrape_fn(query, limit=2)
                n = len(items) if items else 0
                has_magnet = any(
                    (r.get("magnet") or "").startswith("magnet:?xt=urn:btih:")
                    for r in (items or [])
                )
                results[scraper][query] = f"{n} results, magnet ok={has_magnet}"
            except Exception as e:
                results[scraper][query] = f"error: {e}"
    # print table
    print(f"{'Scraper':<14} | {'avatar':<24} | {'led zeppelin':<24} | {'fringe':<24}")
    print("-" * 95)
    for scraper in SCRAPERS:
        row = [scraper[:14].ljust(14)]
        for q in QUERIES:
            v = (results.get(scraper) or {}).get(q) or "-"
            row.append(str(v)[:24].ljust(24))
        print(" | ".join(row))
    print("-" * 95)


if __name__ == "__main__":
    main()
