"""
Utilitários compartilhados pelos scripts de scraping.
Todos os scrapers usam get_url() ou get_url_json() daqui; quando FLARESOLVERR_URL está definido, todas as requisições passam pelo FlareSolverr.
Cada indexador fica em scripts/scraping/{indexer_name}/scrape.py e pode ser afinado independentemente.

Contornar Cloudflare / reCAPTCHA / captcha:
  1. cloudscraper (pip install cloudscraper): usado automaticamente quando instalado.
  2. FlareSolverr: defina FLARESOLVERR_URL=http://localhost:8191 para usar browser real
     (contorna Cloudflare, reCAPTCHA, hCaptcha, Turnstile e afins).
  3. Desativar cloudscraper: SCRAPING_BYPASS_CLOUDFLARE=0

As URLs base (TPB_BASE_URL, YTS_BASE_URL, etc.) vêm do .env na raiz do projeto, se existir.
"""
import html as _html
import json
import os
import re
import sys
from pathlib import Path

# Carrega .env da raiz do projeto para que os scripts usem TPB_BASE_URL, YTS_BASE_URL, etc.
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parents[2]
    load_dotenv(_root / ".env")
except ImportError:
    pass

try:
    import requests
except ImportError:
    requests = None

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

DEFAULT_TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:131.0) Gecko/20100101 Firefox/131.0"

# Padrões que indicam página de bloqueio/captcha (para retry com FlareSolverr)
_BLOCKED_PATTERNS = re.compile(
    r"cloudflare|cf-browser-verification|challenge-running|recaptcha|g-recaptcha|"
    r"hcaptcha|turnstile|captcha|blocked|access denied|just a moment",
    re.I,
)


def _flaresolverr_url() -> str | None:
    url = os.environ.get("FLARESOLVERR_URL", "").strip().rstrip("/")
    return url or None


def _session():
    disable_cf = os.environ.get("SCRAPING_BYPASS_CLOUDFLARE", "").strip().lower() in ("0", "false", "no")
    if cloudscraper is not None and not disable_cf:
        return cloudscraper.create_scraper()
    if requests is None:
        raise RuntimeError("instale requests: pip install requests")
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _is_blocked_page(html: str) -> bool:
    """Indica se o conteúdo parece uma página de bloqueio/captcha."""
    if not html or len(html) < 200:
        return False
    return bool(_BLOCKED_PATTERNS.search(html))


def _fetch_via_flaresolverr(url: str, timeout: int) -> str:
    """Obtém o conteúdo da URL via FlareSolverr (browser real; contorna captcha/reCAPTCHA)."""
    if requests is None:
        raise RuntimeError("requests é necessário para chamar o FlareSolverr")
    base = _flaresolverr_url()
    if not base:
        raise RuntimeError("defina FLARESOLVERR_URL (ex.: http://localhost:8191)")
    endpoint = f"{base}/v1"
    payload = {"cmd": "request.get", "url": url, "maxTimeout": min(timeout * 1000, 60000)}
    r = requests.post(endpoint, json=payload, timeout=timeout + 30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "ok":
        msg = data.get("message", "unknown")
        raise RuntimeError(f"FlareSolverr: {msg}")
    solution = data.get("solution") or {}
    body = solution.get("response") or solution.get("body") or ""
    # FlareSolverr pode devolver HTML com entidades (&amp; etc.); normalizar para URLs/magnets válidos
    return _html.unescape(body)


def _fetch_direct(url: str, timeout: int) -> str:
    """Requisição direta (sem FlareSolverr); usada como fallback quando FlareSolverr retorna 5xx."""
    session = _session()
    if not session.headers.get("User-Agent"):
        session.headers["User-Agent"] = USER_AGENT
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    text = r.text
    if _is_blocked_page(text):
        raise RuntimeError(
            "Resposta parece bloqueio/captcha (Cloudflare, reCAPTCHA, etc.). "
            "Defina FLARESOLVERR_URL (ex.: http://localhost:8191) ou instale cloudscraper."
        )
    return text


def get_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    fs_url = _flaresolverr_url()
    if fs_url:
        try:
            return _fetch_via_flaresolverr(url, timeout)
        except Exception as e:
            # Fallback: quando FlareSolverr falha (5xx, timeout, etc.), tenta requisição direta
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (500, 502, 503, 504) or code is None:
                try:
                    return _fetch_direct(url, timeout)
                except Exception:
                    pass
            raise
    return _fetch_direct(url, timeout)


def get_url_json(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    fs_url = _flaresolverr_url()
    if fs_url:
        raw = _fetch_via_flaresolverr(url, timeout)
        return json.loads(raw)
    session = _session()
    if not session.headers.get("User-Agent"):
        session.headers["User-Agent"] = USER_AGENT
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    text = r.text
    if _is_blocked_page(text):
        raise RuntimeError(
            "Resposta parece bloqueio/captcha (Cloudflare, reCAPTCHA, etc.). "
            "Defina FLARESOLVERR_URL (ex.: http://localhost:8191) ou instale cloudscraper."
        )
    return r.json()


def clean_html_title(t: str) -> str:
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
    return t.strip()


def env_base_url(env_key: str, default: str) -> str:
    return (os.environ.get(env_key, "") or default).strip().rstrip("/")


def output_results(results: list[dict], json_output: bool = True) -> None:
    if json_output:
        out = json.dumps(results, ensure_ascii=False, indent=2)
        try:
            print(out)
        except UnicodeEncodeError:
            sys.stdout.buffer.write((out + "\n").encode("utf-8"))
    else:
        for i, r in enumerate(results, 1):
            title = r.get("title", "?")[:70]
            magnet = (r.get("magnet") or "")[:60]
            torrent_url = r.get("torrent_url") or ""
            print(f"{i}. {title}")
            if magnet:
                print(f"   magnet: {magnet}...")
            if torrent_url:
                print(f"   torrent: {torrent_url}")
            print()


def main_usage(name: str, default_base: str, env_var: str) -> None:
    if len(sys.argv) < 2:
        print(f"Uso: python -m scripts.scraping.{name}.scrape <query> [--no-json]", file=sys.stderr)
        print(f"Env: {env_var} (default: {default_base})", file=sys.stderr)
        sys.exit(1)
