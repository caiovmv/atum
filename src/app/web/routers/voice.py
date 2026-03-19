"""Rotas de voz: busca de coleções e fila para Google Assistant / comando por voz."""

from __future__ import annotations

import random
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ...repositories.playlist_repository_postgres import get_playlist, list_playlists
from ...repositories.radio_repository_postgres import get_sintonia, list_sintonias

router = APIRouter(prefix="/voice", tags=["voice"])


def _track_to_voice(t: dict) -> dict:
    src = t.get("source", "download")
    item_id = t.get("item_id", t.get("id"))
    return {
        "source": src,
        "item_id": item_id,
        "file_index": t.get("file_index", 0),
        "item_name": t.get("item_name", t.get("file_name", "")),
        "artist": t.get("artist"),
    }


@router.get("/collections")
def api_voice_collections(q: str = Query("", description="Termo de busca (nome da playlist ou sintonia)")) -> list[dict]:
    """Retorna playlists e sintonias cujo nome contém o termo (case-insensitive)."""
    term = (q or "").strip().lower()
    if not term:
        return []

    result: list[dict] = []

    try:
        playlists = list_playlists()
        for p in playlists:
            name = (p.get("name") or "").strip()
            if term in name.lower():
                result.append({"type": "playlist", "id": p["id"], "name": name, "kind": p.get("kind", "static")})

        sintonias = list_sintonias()
        for s in sintonias:
            name = (s.get("name") or "").strip()
            if term in name.lower():
                result.append({"type": "sintonia", "id": s["id"], "name": name})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return result


@router.get("/queue")
async def api_voice_queue(
    type_: Literal["playlist", "sintonia"] = Query(..., alias="type"),
    id_: int = Query(..., alias="id"),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """Retorna fila de faixas para reprodução por voz. Playlist dinâmica: gera antes."""
    if type_ == "playlist":
        try:
            p = get_playlist(id_)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        if not p:
            raise HTTPException(status_code=404, detail="Playlist não encontrada.")

        kind = p.get("kind", "static")
        if kind in ("dynamic_rules", "dynamic_ai"):
            from .playlist import generate_playlist_queue
            tracks = await generate_playlist_queue(id_, limit)
        else:
            tracks = p.get("tracks") or []

        return {"tracks": [_track_to_voice(t) for t in tracks], "name": p.get("name", "")}

    if type_ == "sintonia":
        try:
            s = get_sintonia(id_)
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
        if not s:
            raise HTTPException(status_code=404, detail="Sintonia não encontrada.")

        from .radio import _filter_library_by_sintonia, _fetch_item_files
        from .library import get_all_library_items

        items = get_all_library_items()
        rules = s.get("rules") or []
        filtered = _filter_library_by_sintonia(items, rules)
        tracks = []
        for item in filtered:
            files = _fetch_item_files(item)
            item_name = (item.get("name") or "").strip() or "Sem nome"
            artist = (item.get("artist") or "").strip() or None
            for f in files:
                tracks.append({
                    "source": item.get("source", "download"),
                    "item_id": item["id"],
                    "file_index": f.get("index", 0),
                    "item_name": item_name,
                    "artist": artist,
                })
        random.shuffle(tracks)
        queue = tracks[:limit]
        return {"tracks": [_track_to_voice(t) for t in queue], "name": s.get("name", "")}

    raise HTTPException(status_code=400, detail="type deve ser playlist ou sintonia")
