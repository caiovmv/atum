# IPTorrents: stub. Tracker privado; requer cookie de sessao. Nao implementado.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.scraping._common import main_usage, output_results

DEFAULT_BASE = "https://iptorrents.com"


def scrape(query, limit=25):
    return []


def main():
    main_usage("iptorrents", DEFAULT_BASE, "IPTORRENTS_BASE_URL")
    query = sys.argv[1]
    json_out = "--no-json" not in sys.argv
    output_results([], json_output=json_out)
    if not json_out:
        print("(IPTorrents e privado; use cookie/sessao no app principal.)", file=sys.stderr)


if __name__ == "__main__":
    main()
