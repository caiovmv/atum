"""Rotas da Wishlist: GET/POST/DELETE termos, POST /run para buscar e enfileirar."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from ...deps import get_settings
from ...search import DEFAULT_INDEXERS, get_magnet_for_result, search_all
from ...repositories.wishlist_repository import (
    add_term as wishlist_add_term,
    delete_by_id as wishlist_delete_by_id,
    list_all as wishlist_list_all,
)
from pydantic import BaseModel

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

_KEEPALIVE_INTERVAL = 30.0


async def _stream_wishlist_events():
    """Generator SSE: escuta Redis Pub/Sub para eventos da wishlist."""
    from ...event_bus import CHANNEL_WISHLIST, async_subscribe
    try:
        async for channel, data in async_subscribe(CHANNEL_WISHLIST, keepalive_interval=_KEEPALIVE_INTERVAL):
            if channel:
                yield f"data: {json.dumps({'event': 'wishlist_updated'})}\n\n"
            else:
                yield ": keepalive\n\n"
    except (asyncio.CancelledError, GeneratorExit):
        pass


@router.get("/events")
async def wishlist_events():
    """SSE: stream de eventos da wishlist via Redis Pub/Sub."""
    return StreamingResponse(
        _stream_wishlist_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _runner_url(path: str) -> str:
    base = (get_settings().download_runner_url or "").rstrip("/")
    if not base:
        raise HTTPException(
            status_code=503,
            detail="DOWNLOAD_RUNNER_URL não configurado. Inicie o Runner: dl-torrent runner",
        )
    return f"{base}{path}"


@router.get("")
def list_terms(
    request: Request,
    limit: int | None = Query(None, ge=1, le=200, description="Máximo de termos a retornar"),
    offset: int | None = Query(None, ge=0, description="Pular N termos"),
):
    """Lista todos os termos da wishlist (id, term, created_at). ETag para revalidação."""
    data = wishlist_list_all(limit=limit, offset=offset)
    body = json.dumps(data, default=str, ensure_ascii=False)
    etag = hashlib.md5(body.encode()).hexdigest()
    if request.headers.get("if-none-match") == f'"{etag}"':
        return Response(status_code=304)
    return Response(content=body, media_type="application/json", headers={"ETag": f'"{etag}"', "Cache-Control": "private, max-age=0, must-revalidate"})


class AddTermBody(BaseModel):
    term: str


@router.post("")
def add_term(body: AddTermBody) -> dict:
    """Adiciona um termo à wishlist. Retorna { id }."""
    term = (body.term or "").strip()
    if not term:
        raise HTTPException(status_code=400, detail="Termo não pode ser vazio.")
    wid = wishlist_add_term(term)
    if wid <= 0:
        raise HTTPException(status_code=400, detail="Falha ao adicionar (termo duplicado ou inválido).")
    from ...event_bus import CHANNEL_WISHLIST, publish
    publish(CHANNEL_WISHLIST, {"type": "term_added", "id": wid})
    return {"id": wid}


@router.delete("/{term_id}")
def remove_term(term_id: int) -> dict:
    """Remove um termo por id."""
    deleted = wishlist_delete_by_id(term_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Termo não encontrado.")
    from ...event_bus import CHANNEL_WISHLIST, publish
    publish(CHANNEL_WISHLIST, {"type": "term_deleted", "id": term_id})
    return {"ok": True}


class WishlistRunBody(BaseModel):
    term_ids: list[int] | None = None
    lines: list[str] | None = None
    content_type: Literal["music", "movies", "tv"] = "music"
    format_filter: str | None = None
    limit_per_search: int = 5
    save_path: str | None = None
    start_now: bool = True


@router.post("/run")
def run_wishlist(body: WishlistRunBody) -> dict:
    """Para cada termo (term_ids e/ou lines), busca o melhor resultado e enfileira no Runner."""
    terms: list[str] = []
    if body.term_ids:
        all_terms = {r["id"]: r["term"] for r in wishlist_list_all()}
        for tid in body.term_ids:
            if tid in all_terms and (all_terms[tid] or "").strip():
                terms.append(all_terms[tid].strip())
    if body.lines:
        for line in body.lines:
            s = (line or "").strip()
            if s:
                terms.append(s)
    if not terms:
        return {"added": [], "errors": ["Nenhum termo para buscar (informe term_ids e/ou lines)."], "ok": 0, "fail": 1}

    indexer_list = list(DEFAULT_INDEXERS)
    save_path = (body.save_path or "").strip() or get_settings().save_path_for_content_type(body.content_type)
    added: list[int] = []
    errors: list[str] = []
    for query in terms:
        results = search_all(
            query=query,
            limit=min(body.limit_per_search, 100),
            format_filter=body.format_filter,
            no_quality_filter=False,
            verbose=False,
            music_category_only=(body.content_type == "music"),
            content_type=body.content_type,
            indexers=indexer_list,
            sort_by="seeders",
        )
        if not results:
            errors.append(f"Nenhum resultado: {query[:50]}…")
            continue
        result = results[0]
        magnet = get_magnet_for_result(result)
        if not magnet:
            errors.append(f"Sem magnet: {result.title[:50]}…")
            continue
        url = _runner_url("/downloads")
        try:
            resp = httpx.post(
                url,
                json={
                    "magnet": magnet,
                    "save_path": save_path,
                    "name": result.title,
                    "content_type": body.content_type,
                    "start_now": body.start_now,
                },
                timeout=30,
            )
        except httpx.HTTPError as e:
            errors.append(f"Runner: {e}")
            continue
        if resp.status_code != 200:
            errors.append(resp.text or f"HTTP {resp.status_code}")
            continue
        data = resp.json()
        added.append(data.get("id", 0))
    return {"added": added, "errors": errors, "ok": len(added), "fail": len(errors)}
