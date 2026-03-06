"""Rotas de Rádio: sintonias (presets) e fila embaralhada por faixa (músicas aleatórias, não álbum inteiro)."""

from __future__ import annotations

import json
import random
import urllib.parse
from pathlib import Path

import requests
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from starlette.responses import FileResponse

from ...config import get_settings
from ...repositories.radio_repository_postgres import (
    create_sintonia,
    delete_sintonia,
    get_sintonia,
    list_sintonias,
    update_sintonia,
)
from .library import get_all_library_items, _runner_url

router = APIRouter(prefix="/radio", tags=["radio"])


class RuleBody(BaseModel):
    kind: str = "include"  # include | exclude
    type: str = "content_type"  # content_type | genre | artist | tag | item
    value: str | dict | list  # string ou para item: {"source": "download"|"import", "id": int}


class SintoniaCreateBody(BaseModel):
    name: str
    rules: list[RuleBody] = []


class SintoniaUpdateBody(BaseModel):
    name: str | None = None
    rules: list[RuleBody] | None = None


def _item_matches_rule(item: dict, rule: dict) -> bool:
    kind = (rule.get("kind") or "include").lower()
    type_ = (rule.get("type") or "content_type").lower()
    value = rule.get("value")
    if value is None:
        return False
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            pass
    if type_ == "content_type":
        ct = (item.get("content_type") or "").strip().lower()
        v = (value if isinstance(value, str) else str(value)).strip().lower()
        return ct == v
    if type_ == "genre":
        g = (item.get("genre") or "").strip().lower()
        v = (value if isinstance(value, str) else str(value)).strip().lower()
        return v in g or g == v
    if type_ == "artist":
        a = (item.get("artist") or "").strip().lower()
        v = (value if isinstance(value, str) else str(value)).strip().lower()
        return v in a or a == v
    if type_ == "tag":
        tags = item.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        v = (value if isinstance(value, str) else str(value)).strip().lower()
        return any(v in (t or "").lower() for t in tags) or v in [str(t).lower() for t in tags]
    if type_ == "item":
        if not isinstance(value, dict):
            try:
                value = json.loads(value) if isinstance(value, str) else {}
            except (ValueError, TypeError):
                return False
        src = value.get("source") or "download"
        iid = value.get("id")
        if iid is None:
            return False
        return item.get("source") == src and item.get("id") == int(iid)
    return False


def _filter_library_by_sintonia(items: list[dict], rules: list[dict]) -> list[dict]:
    include_rules = [r for r in rules if (r.get("kind") or "include").lower() == "include"]
    exclude_rules = [r for r in rules if (r.get("kind") or "").lower() == "exclude"]
    if include_rules:
        out = []
        for item in items:
            if any(_item_matches_rule(item, r) for r in include_rules):
                out.append(item)
    else:
        out = list(items)
    for r in exclude_rules:
        out = [x for x in out if not _item_matches_rule(x, r)]
    return out


@router.get("/sintonias")
def api_list_sintonias() -> list[dict]:
    """Lista todas as sintonias."""
    try:
        return list_sintonias()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sintonias/{sintonia_id}")
def api_get_sintonia(sintonia_id: int) -> dict:
    """Detalhe de uma sintonia (com regras)."""
    try:
        s = get_sintonia(sintonia_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not s:
        raise HTTPException(status_code=404, detail="Sintonia não encontrada.")
    return s


def _rules_to_repo(rules: list[RuleBody]) -> list[dict]:
    out = []
    for r in rules:
        v = r.value
        if isinstance(v, (dict, list)):
            v = json.dumps(v)
        out.append({"kind": r.kind, "type": r.type, "value": v})
    return out


@router.post("/sintonias")
def api_create_sintonia(body: SintoniaCreateBody) -> dict:
    """Cria uma sintonia."""
    try:
        rules = _rules_to_repo(body.rules)
        sid = create_sintonia(body.name.strip(), rules)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"id": sid, "name": body.name.strip()}


@router.patch("/sintonias/{sintonia_id}")
def api_update_sintonia(sintonia_id: int, body: SintoniaUpdateBody) -> dict:
    """Atualiza nome e/ou regras da sintonia."""
    try:
        rules = _rules_to_repo(body.rules) if body.rules is not None else None
        ok = update_sintonia(sintonia_id, name=body.name.strip() if body.name else None, rules=rules)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Sintonia não encontrada.")
    return {"id": sintonia_id}


@router.delete("/sintonias/{sintonia_id}")
def api_delete_sintonia(sintonia_id: int) -> dict:
    """Remove uma sintonia."""
    try:
        ok = delete_sintonia(sintonia_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Sintonia não encontrada.")
    return {"id": sintonia_id}


def _radio_cover_dir() -> Path:
    """Diretório para capas das sintonias (covers_path/radio)."""
    d = get_settings().covers_path / "radio"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.get("/cover/{sintonia_id}")
def api_radio_cover(sintonia_id: int) -> FileResponse:
    """Serve a capa da sintonia (imagem customizada)."""
    s = get_sintonia(sintonia_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sintonia não encontrada.")
    cover_path = (s.get("cover_path") or "").strip()
    if not cover_path:
        raise HTTPException(status_code=404, detail="Capa não definida.")
    full = get_settings().covers_path / cover_path
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Capa não encontrada.")
    return FileResponse(full, media_type="image/jpeg")


@router.post("/sintonias/{sintonia_id}/cover")
def api_upload_radio_cover(sintonia_id: int, file: UploadFile = File(...)) -> dict:
    """Envia uma imagem como capa da sintonia (substitui a anterior)."""
    s = get_sintonia(sintonia_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sintonia não encontrada.")
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Envie um arquivo de imagem (JPEG, PNG, etc.).")
    ext = ".jpg"
    if "png" in content_type:
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"
    dest_dir = _radio_cover_dir()
    dest = dest_dir / f"{sintonia_id}{ext}"
    try:
        data = file.file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Arquivo vazio.")
        dest.write_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    relative = f"radio/{sintonia_id}{ext}"
    try:
        update_sintonia(sintonia_id, cover_path=relative)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"id": sintonia_id, "cover_path": relative}


def _fetch_item_files(item: dict) -> list[dict]:
    """Retorna lista de arquivos de mídia do item (Runner). Cada elemento: { index, name, size }."""
    try:
        if item.get("source") == "import":
            cp = (item.get("content_path") or "").strip()
            if not cp:
                return []
            url = _runner_url("/library-import/files") + "?" + urllib.parse.urlencode({"content_path": cp})
        else:
            url = _runner_url(f"/downloads/{item['id']}/files")
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        files = data.get("files") or []
        return [f for f in files if isinstance(f, dict) and f.get("index") is not None]
    except Exception:
        return []


@router.post("/sintonias/{sintonia_id}/queue")
def api_sintonia_queue(
    sintonia_id: int,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """Retorna fila embaralhada de faixas (uma música por vez, não álbum inteiro) que respeitam a sintonia."""
    try:
        s = get_sintonia(sintonia_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not s:
        raise HTTPException(status_code=404, detail="Sintonia não encontrada.")
    items = get_all_library_items()
    rules = s.get("rules") or []
    filtered = _filter_library_by_sintonia(items, rules)
    tracks: list[dict] = []
    for item in filtered:
        files = _fetch_item_files(item)
        item_name = (item.get("name") or "").strip() or "Sem nome"
        artist = (item.get("artist") or "").strip() or None
        for f in files:
            idx = f.get("index", 0)
            name = (f.get("name") or "").strip() or f"Faixa {idx + 1}"
            tracks.append({
                "id": item["id"],
                "source": item.get("source") or "download",
                "file_index": idx,
                "file_name": name,
                "item_name": item_name,
                "artist": artist,
            })
    random.shuffle(tracks)
    queue = tracks[:limit]
    return {"tracks": queue}
