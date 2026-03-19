"""Router de Chat AI — conversa contextual com o LLM configurado."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...ai.prompts_registry import get_prompt_temperature, get_system_prompt
from ...deps import get_settings_repo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context: dict | None = None


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str


class SmartQueueRequest(BaseModel):
    prompt: str
    library_items: list[dict] | None = None


class SmartQueueResponse(BaseModel):
    ids: list[int]
    explanation: str


@router.post("/chat/queue")
async def smart_queue(body: SmartQueueRequest) -> SmartQueueResponse:
    """Usa o LLM para selecionar faixas da biblioteca baseado em um prompt de mood/estilo."""
    from ...ai.llm_client import LLMClient

    client = LLMClient.from_settings()
    if not client:
        raise HTTPException(status_code=503, detail="AI não configurado.")

    items_desc = ""
    if body.library_items:
        lines: list[str] = []
        for item in body.library_items[:50]:
            parts = [f"ID={item.get('id')}: {item.get('name', '?')}"]
            if item.get("artist"):
                parts.append(f"by {item['artist']}")
            tags: list[str] = []
            if item.get("genre"):
                tags.append(item["genre"])
            if item.get("moods"):
                moods = item["moods"] if isinstance(item["moods"], list) else []
                if moods:
                    tags.append(f"mood:{','.join(moods[:3])}")
            if item.get("sub_genres"):
                sgs = item["sub_genres"] if isinstance(item["sub_genres"], list) else []
                if sgs:
                    tags.append(f"style:{','.join(sgs[:2])}")
            if item.get("bpm"):
                tags.append(f"BPM:{item['bpm']}")
            if tags:
                parts.append(f"[{'; '.join(tags)}]")
            lines.append(" ".join(parts))
        items_desc = "\n".join(lines)

    repo = _get_repo_or_default()
    sys_prompt = get_system_prompt("smart_queue", repo)
    temp = get_prompt_temperature("smart_queue", repo)

    user_prompt = f"Pedido: {body.prompt}\n\nBiblioteca disponível:\n{items_desc}"
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        resp = await asyncio.to_thread(client.chat, messages, temp)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    import json as _json
    text = resp.content.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            data = _json.loads(text[start:end])
            ids = [int(x) for x in (data.get("ids") or []) if isinstance(x, (int, float))]
            return SmartQueueResponse(ids=ids, explanation=data.get("explanation", ""))
        except (ValueError, _json.JSONDecodeError):
            pass

    return SmartQueueResponse(ids=[], explanation=text)


def _get_repo_or_default():
    repo = get_settings_repo()
    return repo if repo is not None else {"ai_prompts": {}}


def _build_chat_messages(body: ChatRequest) -> list[dict]:
    repo = _get_repo_or_default()
    system_content = get_system_prompt("chat_receiver", repo)
    if body.context:
        ctx_parts: list[str] = []
        if body.context.get("track"):
            ctx_parts.append(f"Faixa: {body.context['track']}")
        if body.context.get("artist"):
            ctx_parts.append(f"Artista: {body.context['artist']}")
        if body.context.get("album"):
            ctx_parts.append(f"Álbum: {body.context['album']}")
        codec = body.context.get("codec")
        bitrate = body.context.get("bitrate")
        if codec or bitrate:
            quality = codec or ""
            if bitrate:
                quality += f" {bitrate}" if quality else str(bitrate)
            is_lossy = codec and codec.upper() in ("MP3", "AAC", "OGG", "OPUS", "WMA")
            quality += " (lossy — cuidado com boost em altas frequências)" if is_lossy else " (lossless)" if codec else ""
            ctx_parts.append(f"Qualidade: {quality}")
        vol = body.context.get("volume")
        if vol is not None:
            ctx_parts.append(f"Volume: {vol}%")
            if vol < 40:
                ctx_parts.append("⚠ Volume baixo — considere sugerir LOUDNESS ON para compensação Fletcher-Munson")
        eq_parts = []
        for k in ("bass", "mid", "treble"):
            v = body.context.get(k)
            if v is not None:
                eq_parts.append(f"{k.upper()}: {'+' if v > 0 else ''}{v}dB")
        if eq_parts:
            ctx_parts.append(f"EQ atual: {', '.join(eq_parts)}")
        if ctx_parts:
            system_content += "\n\n--- Estado do Receiver ---\n" + "\n".join(ctx_parts)

    messages = [{"role": "system", "content": system_content}]
    for msg in body.messages:
        messages.append({"role": msg.role, "content": msg.content})
    return messages


@router.post("/chat")
async def chat(body: ChatRequest) -> ChatResponse:
    """Envia mensagens para o LLM e retorna a resposta."""
    from ...ai.llm_client import LLMClient

    client = LLMClient.from_settings()
    if not client:
        raise HTTPException(status_code=503, detail="AI não configurado. Configure provider e modelo nas Configurações.")

    repo = _get_repo_or_default()
    temp = get_prompt_temperature("chat_receiver", repo)
    messages = _build_chat_messages(body)
    try:
        resp = await asyncio.to_thread(client.chat, messages, temp)
    except Exception as e:
        logger.warning("Chat LLM error: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro ao contactar LLM: {e}") from e

    return ChatResponse(content=resp.content, model=resp.model, provider=resp.provider)


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest):
    """Streaming chat via SSE — envia chunks de texto conforme o LLM gera."""
    from ...ai.llm_client import LLMClient
    from starlette.responses import StreamingResponse

    client = LLMClient.from_settings()
    if not client:
        raise HTTPException(status_code=503, detail="AI não configurado.")

    repo = _get_repo_or_default()
    temp = get_prompt_temperature("chat_receiver", repo)
    messages = _build_chat_messages(body)

    _SENTINEL = object()

    async def generate():
        queue: asyncio.Queue[str | object] = asyncio.Queue()

        def _produce():
            try:
                for chunk in client.chat_stream(messages, temp):
                    queue.put_nowait(f"data: {chunk}\n\n")
            except Exception as e:
                logger.warning("Chat stream error: %s", e)
                queue.put_nowait(f"event: error\ndata: {e}\n\n")
            finally:
                queue.put_nowait(_SENTINEL)

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _produce)

        while True:
            item = await queue.get()
            if item is _SENTINEL:
                break
            yield item  # type: ignore[misc]
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
