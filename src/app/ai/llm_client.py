"""Abstração de LLM client para Ollama e OpenRouter (formato OpenAI-compatible)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

_OLLAMA_CHAT_PATH = "/api/chat"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_TIMEOUT = 120


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str


class LLMClient:
    """Client unificado para Ollama (local) e OpenRouter (cloud)."""

    def __init__(
        self,
        provider: str,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        fallback_provider: str | None = None,
        fallback_model: str | None = None,
        fallback_api_key: str | None = None,
        fallback_base_url: str | None = None,
        timeout: int = _TIMEOUT,
    ) -> None:
        self.provider = provider
        self.model = model
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.api_key = api_key
        self.fallback_provider = fallback_provider
        self.fallback_model = fallback_model
        self.fallback_api_key = fallback_api_key
        self.fallback_base_url = (fallback_base_url or "").rstrip("/") or None
        self.timeout = timeout

    @classmethod
    def from_settings(cls) -> LLMClient | None:
        """Cria instância a partir de app_settings. Retorna None se não configurado."""
        from ..deps import get_settings_repo

        repo = get_settings_repo()
        if not repo:
            return None

        provider = repo.get("ai_provider") or "ollama"
        model = repo.get("ai_model") or "llama3.1:8b"
        api_key = repo.get("ai_api_key") or ""
        base_url = repo.get("ai_base_url") or "http://ollama:11434"
        fallback_provider = repo.get("ai_fallback_provider") or ""
        fallback_model = repo.get("ai_fallback_model") or ""
        fallback_api_key = repo.get("ai_fallback_api_key") or ""
        fallback_base_url = repo.get("ai_fallback_base_url") or ""

        return cls(
            provider=str(provider),
            model=str(model),
            base_url=str(base_url),
            api_key=str(api_key) if api_key else None,
            fallback_provider=str(fallback_provider) if fallback_provider else None,
            fallback_model=str(fallback_model) if fallback_model else None,
            fallback_api_key=str(fallback_api_key) if fallback_api_key else None,
            fallback_base_url=str(fallback_base_url) if fallback_base_url else None,
        )

    def chat(self, messages: list[dict], temperature: float = 0.3) -> LLMResponse:
        """Envia mensagem e retorna resposta. Tenta fallback se o provider primário falhar."""
        try:
            return self._call(self.provider, self.model, self.base_url, self.api_key, messages, temperature)
        except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError) as primary_err:
            if self.fallback_provider and self.fallback_model:
                logger.warning("LLM primário falhou (%s), tentando fallback (%s): %s", self.provider, self.fallback_provider, primary_err)
                fb_base = self.fallback_base_url or (self.base_url if self.fallback_provider == "ollama" else None)
                return self._call(self.fallback_provider, self.fallback_model, fb_base, self.fallback_api_key, messages, temperature)
            raise

    def _call(
        self,
        provider: str,
        model: str,
        base_url: str | None,
        api_key: str | None,
        messages: list[dict],
        temperature: float,
    ) -> LLMResponse:
        if provider == "ollama":
            return self._call_ollama(model, base_url or "http://localhost:11434", messages, temperature)
        return self._call_openai_compatible(provider, model, base_url, api_key, messages, temperature)

    def _call_ollama(self, model: str, base_url: str, messages: list[dict], temperature: float) -> LLMResponse:
        url = f"{base_url.rstrip('/')}{_OLLAMA_CHAT_PATH}"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        r = requests.post(url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        content = data.get("message", {}).get("content", "")
        return LLMResponse(content=content, model=model, provider="ollama")

    def _call_openai_compatible(
        self,
        provider: str,
        model: str,
        base_url: str | None,
        api_key: str | None,
        messages: list[dict],
        temperature: float,
    ) -> LLMResponse:
        if provider == "openrouter":
            url = _OPENROUTER_URL
        elif base_url:
            url = f"{base_url.rstrip('/')}/v1/chat/completions"
        else:
            url = _OPENROUTER_URL

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices") or []
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        return LLMResponse(content=content, model=model, provider=provider)

    def chat_json(self, messages: list[dict], temperature: float = 0.2) -> dict:
        """Chat que espera resposta JSON. Extrai JSON do conteúdo retornado."""
        resp = self.chat(messages, temperature)
        text = resp.content.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            logger.warning("LLM retornou conteúdo não-JSON: %s", resp.content[:200])
            return {}
