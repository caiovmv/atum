"""Router para System Prompts: listar, editar e dry-run."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...ai.llm_client import LLMClient
from ...ai.prompts_registry import PROMPTS, get_prompt_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/prompts", tags=["ai-prompts"])


def _get_repo():
    from ...deps import get_settings_repo
    repo = get_settings_repo()
    if not repo:
        raise HTTPException(status_code=503, detail="Settings não configurado.")
    return repo


class PromptUpdateBody(BaseModel):
    system: str | None = None
    temperature: float | None = None


class DryRunBody(BaseModel):
    user_input: str = ""
    context: dict[str, Any] | None = None


def _build_dry_run_messages(prompt_id: str, user_input: str, context: dict | None, repo: Any) -> list[dict]:
    """Constrói mensagens para dry-run conforme o prompt_id."""
    config = get_prompt_config(prompt_id, repo)
    system = config["system"]

    if prompt_id == "chat_receiver":
        system_content = system
        if context:
            ctx_parts = []
            if context.get("track"):
                ctx_parts.append(f"Faixa: {context['track']}")
            if context.get("artist"):
                ctx_parts.append(f"Artista: {context['artist']}")
            if context.get("album"):
                ctx_parts.append(f"Álbum: {context['album']}")
            if context.get("codec") or context.get("bitrate"):
                quality = context.get("codec", "") or ""
                if context.get("bitrate"):
                    quality += f" {context['bitrate']}" if quality else str(context["bitrate"])
                ctx_parts.append(f"Qualidade: {quality}")
            if context.get("volume") is not None:
                ctx_parts.append(f"Volume: {context['volume']}%")
            for k in ("bass", "mid", "treble"):
                v = context.get(k)
                if v is not None:
                    ctx_parts.append(f"{k.upper()}: {'+' if v > 0 else ''}{v}dB")
            if ctx_parts:
                system_content += "\n\n--- Estado do Receiver ---\n" + "\n".join(ctx_parts)
        user_content = user_input or "Sugira um EQ para jazz suave."
        return [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}]

    if prompt_id == "smart_queue":
        items_desc = ""
        library_items = None
        if context and context.get("library_items"):
            raw = context["library_items"]
            if isinstance(raw, str):
                try:
                    library_items = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    library_items = []
            else:
                library_items = raw
        if library_items:
            lines = []
            for item in (library_items or [])[:20]:
                parts = [f"ID={item.get('id')}: {item.get('name', '?')}"]
                if item.get("artist"):
                    parts.append(f"by {item['artist']}")
                if item.get("genre"):
                    parts.append(f"[{item['genre']}]")
                lines.append(" ".join(parts))
            items_desc = "\n".join(lines) if lines else ""
        user_content = f"Pedido: {user_input or 'rock energético para treino'}\n\nBiblioteca disponível:\n{items_desc}"
        return [{"role": "system", "content": system}, {"role": "user", "content": user_content}]

    if prompt_id == "playlist_ai":
        lib_raw = context.get("library_lines", "") if context else ""
        lib_lines = lib_raw.split("\n") if isinstance(lib_raw, str) else (lib_raw or [])
        lib_lines = [l.strip() for l in lib_lines if l.strip()]
        if not lib_lines:
            lib_lines = ["ID=1: Track A by Artist X [rock]", "ID=2: Track B by Artist Y [jazz]"]
        user_content = f"Pedido: {user_input or 'jazz para relaxar'}\n\nBiblioteca:\n" + "\n".join(lib_lines[:20])
        return [{"role": "system", "content": system}, {"role": "user", "content": user_content}]

    if prompt_id == "recommendations":
        profile = context or {}
        def _to_list(v):
            if isinstance(v, list):
                return v
            if isinstance(v, str):
                return [x.strip() for x in v.split(",") if x.strip()]
            return []
        top_genres = _to_list(profile.get("top_genres")) or ["rock", "jazz"]
        top_artists = _to_list(profile.get("top_artists")) or ["Artist A", "Artist B"]
        existing = _to_list(profile.get("existing_names")) or ["Album X", "Album Y"]
        user_content = (
            f"PERFIL DO USUÁRIO:\n"
            f"- Biblioteca: {profile.get('library_size', 100)} itens\n"
            f"- Gêneros: {', '.join(top_genres)}\n"
            f"- Artistas: {', '.join(top_artists)}\n"
            f"- Moods: {', '.join(_to_list(profile.get('top_moods')) or ['energético'])}\n\n"
            f"JÁ NA BIBLIOTECA (amostra): {', '.join(existing[:10])}\n\n"
            f"Sugira até 5 itens para wishlist E até 3 feeds RSS."
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user_content}]

    if prompt_id == "enrichment":
        user_content = (
            f"Artista: {context.get('artist', 'Unknown')}\n"
            f"Álbum: {context.get('album', 'Unknown')}\n"
            f"Gênero: {context.get('genre', 'unknown')}\n"
            f"BPM: {context.get('bpm', '?')} | Energy: {context.get('energy', '?')} | Valence: {context.get('valence', '?')}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user_content}]

    if prompt_id == "parse_torrent":
        user_content = user_input or "Artist - Album (2020) [FLAC]"
        return [{"role": "system", "content": system}, {"role": "user", "content": user_content}]

    if prompt_id == "fix_metadata":
        ctx = context or {}
        parts = [f"Filename: {ctx.get('filename', '01 - Track.flac')}"]
        if ctx.get("folder_path"):
            parts.append(f"Folder path: {ctx['folder_path']}")
        existing = ctx.get("existing")
        if existing:
            if isinstance(existing, str):
                try:
                    existing = json.loads(existing)
                except (json.JSONDecodeError, TypeError):
                    existing = {}
            parts.append(f"Existing tags: {json.dumps(existing)}")
        user_content = "\n".join(parts)
        return [{"role": "system", "content": system}, {"role": "user", "content": user_content}]

    if prompt_id == "detect_content_type":
        user_content = user_input or "Show.Name.S02E05.720p.WEB-DL"
        return [{"role": "system", "content": system}, {"role": "user", "content": user_content}]

    return [{"role": "system", "content": system}, {"role": "user", "content": user_input or "test"}]


@router.get("")
def list_prompts() -> list[dict]:
    """Lista todos os prompts com metadados, config atual e schemas."""
    repo = _get_repo()
    overrides = repo.get("ai_prompts") or {}
    result = []
    for pid, meta in PROMPTS.items():
        override = overrides.get(pid) or {}
        config = get_prompt_config(pid, repo)
        item = {
            "id": pid,
            "label": meta["label"],
            "description": meta["description"],
            "system": config["system"],
            "temperature": config["temperature"],
            "default_temperature": meta["default_temperature"],
        }
        if "context_schema" in meta:
            item["context_schema"] = meta["context_schema"]
        if "expected_json_schema" in meta:
            item["expected_json_schema"] = meta["expected_json_schema"]
        if "response_type" in meta:
            item["response_type"] = meta["response_type"]
        result.append(item)
    return result


@router.get("/{prompt_id}")
def get_prompt(prompt_id: str) -> dict:
    """Retorna config de um prompt."""
    if prompt_id not in PROMPTS:
        raise HTTPException(status_code=404, detail="Prompt não encontrado.")
    repo = _get_repo()
    config = get_prompt_config(prompt_id, repo)
    meta = PROMPTS[prompt_id]
    item = {
        "id": prompt_id,
        "label": meta["label"],
        "description": meta["description"],
        "system": config["system"],
        "temperature": config["temperature"],
        "default_temperature": meta["default_temperature"],
    }
    if "context_schema" in meta:
        item["context_schema"] = meta["context_schema"]
    if "expected_json_schema" in meta:
        item["expected_json_schema"] = meta["expected_json_schema"]
    if "response_type" in meta:
        item["response_type"] = meta["response_type"]
    return item


@router.patch("/{prompt_id}")
def update_prompt(prompt_id: str, body: PromptUpdateBody) -> dict:
    """Atualiza system e/ou temperature de um prompt."""
    if prompt_id not in PROMPTS:
        raise HTTPException(status_code=404, detail="Prompt não encontrado.")
    repo = _get_repo()
    overrides = dict(repo.get("ai_prompts") or {})
    current = overrides.get(prompt_id) or {}
    if body.system is not None:
        current["system"] = body.system
    if body.temperature is not None:
        current["temperature"] = body.temperature
    overrides[prompt_id] = current
    repo.set_many({"ai_prompts": overrides})
    return {"ok": True, "id": prompt_id}


@router.post("/{prompt_id}/dry-run")
async def dry_run_prompt(prompt_id: str, body: DryRunBody) -> dict:
    """Executa dry-run: envia mensagens ao LLM e retorna resposta sem executar ação."""
    if prompt_id not in PROMPTS:
        raise HTTPException(status_code=404, detail="Prompt não encontrado.")
    client = LLMClient.from_settings()
    if not client:
        raise HTTPException(status_code=503, detail="AI não configurado.")
    repo = _get_repo()
    config = get_prompt_config(prompt_id, repo)
    user_input = (body.context or {}).get("user_input") or body.user_input
    messages = _build_dry_run_messages(prompt_id, user_input, body.context, repo)
    try:
        resp = await asyncio.to_thread(client.chat, messages, config["temperature"])
    except Exception as e:
        logger.warning("Dry-run LLM error: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    all_messages = messages + [{"role": "assistant", "content": resp.content}]
    return {
        "messages": all_messages,
        "response": {"content": resp.content, "model": resp.model, "provider": resp.provider},
    }
