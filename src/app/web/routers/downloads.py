"""Proxy para o Download Runner: /api/downloads (GET, POST, start, stop, delete)."""

from __future__ import annotations

import urllib.parse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ...deps import get_settings

router = APIRouter()

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
    return _client


def _runner_url(path: str) -> str:
    base = (get_settings().download_runner_url or "").rstrip("/")
    if not base:
        raise HTTPException(
            status_code=503,
            detail="DOWNLOAD_RUNNER_URL não configurado. Inicie o Runner: dl-torrent runner",
        )
    return f"{base}{path}"


@router.get("/downloads/events")
async def downloads_events(status: str | None = Query(None)):
    """SSE: proxy do stream de eventos de downloads do Runner (atualização ~1s)."""
    path = "/downloads/events" + ("?" + urllib.parse.urlencode({"status": status}) if status else "")
    url = _runner_url(path)
    client = _get_client()
    try:
        req = client.build_request("GET", url)
        resp = await client.send(req, stream=True)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner indisponível: {e}") from e
    if resp.status_code != 200:
        body = await resp.aread()
        await resp.aclose()
        raise HTTPException(status_code=resp.status_code, detail=body.decode(errors="replace") or "Erro no Runner")

    async def _stream():
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await resp.aclose()

    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get("/downloads")
async def list_downloads(status: str | None = Query(None)) -> list[dict]:
    """Lista downloads (proxy para o Runner)."""
    path = "/downloads" + ("?" + urllib.parse.urlencode({"status": status}) if status else "")
    url = _runner_url(path)
    client = _get_client()
    try:
        r = await client.get(url)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text or "Erro no Runner")
        return r.json()
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner indisponível: {e}") from e
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=502, detail=f"Resposta inválida do Runner: {e}") from e


@router.post("/downloads")
async def add_download(body: dict) -> dict:
    """Adiciona download (proxy para o Runner)."""
    url = _runner_url("/downloads")
    client = _get_client()
    try:
        r = await client.post(url, json=body)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner indisponível: {e}") from e
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.post("/downloads/{download_id}/start")
async def start_download(download_id: int) -> dict:
    url = _runner_url(f"/downloads/{download_id}/start")
    client = _get_client()
    try:
        r = await client.post(url)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner indisponível: {e}") from e
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.post("/downloads/{download_id}/stop")
async def stop_download(download_id: int) -> dict:
    url = _runner_url(f"/downloads/{download_id}/stop")
    client = _get_client()
    try:
        r = await client.post(url)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner indisponível: {e}") from e
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.delete("/downloads/{download_id}")
async def delete_download(download_id: int, remove_files: bool = Query(False)) -> dict:
    qs = urllib.parse.urlencode({"remove_files": str(remove_files).lower()})
    url = _runner_url(f"/downloads/{download_id}?{qs}")
    client = _get_client()
    try:
        r = await client.delete(url)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner indisponível: {e}") from e
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.post("/torrent/metadata")
async def get_torrent_metadata(body: dict) -> dict:
    """Retorna nome e lista de arquivos do torrent (proxy para o Runner)."""
    url = _runner_url("/torrent/metadata")
    client = _get_client()
    try:
        r = await client.post(url, json=body, timeout=httpx.Timeout(260.0, connect=10.0))
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text or "Erro no Runner")
        return r.json()
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Runner indisponível: {e}") from e
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=502, detail=f"Resposta inválida do Runner: {e}") from e
