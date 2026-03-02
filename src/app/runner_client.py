"""Cliente HTTP para o Download Runner (uso do CLI em modo remoto)."""

from __future__ import annotations

import urllib.parse

import requests

from .config import get_settings


def _base_url() -> str | None:
    url = (get_settings().download_runner_url or "").strip().rstrip("/")
    return url or None


def is_runner_available(timeout: float = 2.0) -> str | None:
    """Retorna a URL base do Runner se estiver configurada e acessível; senão None."""
    base = _base_url()
    if not base:
        return None
    try:
        r = requests.get(f"{base}/downloads", timeout=timeout)
        if r.status_code in (200, 404):
            return base
    except requests.RequestException:
        pass
    return None


def runner_list_downloads(status: str | None = None) -> list[dict] | None:
    """Lista downloads via Runner. Retorna None se Runner indisponível."""
    base = is_runner_available()
    if not base:
        return None
    path = "/downloads" + ("?" + urllib.parse.urlencode({"status": status}) if status else "")
    try:
        r = requests.get(f"{base}{path}", timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except requests.RequestException:
        return None


def runner_add(magnet: str, save_path: str, name: str | None = None, content_type: str | None = None, start_now: bool = True) -> int | None:
    """Adiciona download via Runner. Retorna id ou None."""
    base = is_runner_available()
    if not base:
        return None
    try:
        r = requests.post(
            f"{base}/downloads",
            json={
                "magnet": magnet,
                "save_path": save_path,
                "name": name,
                "content_type": content_type,
                "start_now": start_now,
            },
            timeout=10,
        )
        if r.status_code != 200:
            return None
        return r.json().get("id")
    except requests.RequestException:
        return None


def runner_start(download_id: int) -> bool:
    """Inicia download via Runner."""
    base = is_runner_available()
    if not base:
        return False
    try:
        r = requests.post(f"{base}/downloads/{download_id}/start", timeout=10)
        return r.status_code == 200
    except requests.RequestException:
        return False


def runner_stop(download_id: int) -> bool:
    """Para download via Runner."""
    base = is_runner_available()
    if not base:
        return False
    try:
        r = requests.post(f"{base}/downloads/{download_id}/stop", timeout=10)
        return r.status_code == 200
    except requests.RequestException:
        return False


def runner_delete(download_id: int, remove_files: bool = False) -> bool:
    """Remove download via Runner."""
    base = is_runner_available()
    if not base:
        return False
    try:
        r = requests.delete(f"{base}/downloads/{download_id}", params={"remove_files": remove_files}, timeout=10)
        return r.status_code == 200
    except requests.RequestException:
        return False
