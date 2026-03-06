"""
Diagnóstico dos scrapers que retornam 0: verifica se get_url falha ou se o HTML não tem magnet.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from scripts.scraping._common import get_url, env_base_url

def main():
    fs = os.environ.get("FLARESOLVERR_URL", "").strip()
    print("FLARESOLVERR_URL:", fs or "(not set)")
    print()

    # Indexadores removidos (tg, torlock, speedtorrent, fitgirl, rutracker, rarbg, ext).
    # Para diagnosticar outros scrapers, adicione (nome, base_url, path_busca).
    cases: list[tuple[str, str, str]] = []
    for name, base, path in cases:
        url = base.rstrip("/") + path
        print(f"--- {name} ---")
        print(f"  URL: {url}")
        try:
            html = get_url(url)
            print(f"  OK len={len(html)}")
            has_magnet = "magnet:?xt=" in html
            print(f"  has 'magnet:?xt=': {has_magnet}")
            if has_magnet:
                n = len(re.findall(r'href="(magnet:\?xt=[^"]+)"', html, re.I))
                print(f"  magnet links count: {n}")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
        print()
    print("Done.")

if __name__ == "__main__":
    main()
