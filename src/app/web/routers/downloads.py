"""Proxy para o Download Runner: /api/downloads (GET, POST, start, stop, delete)."""

from __future__ import annotations

import urllib.parse

import requests
from fastapi import APIRouter, HTTPException, Query

from ...deps import get_settings

router = APIRouter()


def _runner_url(path: str) -> str:
    base = (get_settings().download_runner_url or "").rstrip("/")
    if not base:
        raise HTTPException(
            status_code=503,
            detail="DOWNLOAD_RUNNER_URL não configurado. Inicie o Runner: dl-torrent runner",
        )
    return f"{base}{path}"


def _proxy_to_runner(method: str, path: str, **kwargs) -> requests.Response:
    url = _runner_url(path)
    try:
        r = requests.request(method, url, timeout=30, **kwargs)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Runner indisponível: {e}") from e
    return r


@router.get("/downloads")
def list_downloads(status: str | None = Query(None)) -> list[dict]:
    """Lista downloads (proxy para o Runner)."""
    path = "/downloads" + ("?" + urllib.parse.urlencode({"status": status}) if status else "")
    r = _proxy_to_runner("GET", path)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.post("/downloads")
def add_download(body: dict) -> dict:
    """Adiciona download (proxy para o Runner)."""
    r = _proxy_to_runner("POST", "/downloads", json=body)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.post("/downloads/{download_id}/start")
def start_download(download_id: int) -> dict:
    r = _proxy_to_runner("POST", f"/downloads/{download_id}/start")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.post("/downloads/{download_id}/stop")
def stop_download(download_id: int) -> dict:
    r = _proxy_to_runner("POST", f"/downloads/{download_id}/stop")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.delete("/downloads/{download_id}")
def delete_download(download_id: int, remove_files: bool = Query(False)) -> dict:
    qs = urllib.parse.urlencode({"remove_files": str(remove_files).lower()})
    r = _proxy_to_runner("DELETE", f"/downloads/{download_id}?{qs}")
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()
