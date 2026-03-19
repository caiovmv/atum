"""Repositório de app_settings para PostgreSQL."""

from __future__ import annotations

import json
from typing import Any

from ..db_postgres import connection_postgres


# Chaves conhecidas com seus defaults e tipos
SETTINGS_DEFAULTS: dict[str, Any] = {
    # Organização
    "post_process_enabled": False,
    "organize_mode": "in_place",
    "plex_naming_enabled": True,
    "include_tmdb_id_in_folder": True,
    "include_imdb_id_in_folder": False,
    # Integração TMDB
    "tmdb_api_key": "",
    # Integração Plex
    "plex_url": "",
    "plex_token": "",
    "plex_section_ids": "",
    "plex_auto_scan": False,
    # Integração Jellyfin
    "jellyfin_url": "",
    "jellyfin_api_key": "",
    "jellyfin_auto_scan": False,
    # Integração Last.fm
    "lastfm_api_key": "",
    # Integração Spotify
    "spotify_client_id": "",
    "spotify_client_secret": "",
    # Qualidade
    "auto_upgrade_quality": False,
    "preferred_video_quality": ["2160p", "1080p", "720p", "480p"],
    "preferred_music_quality": ["FLAC", "320", "V0", "V2", "256"],
    # Paths (override do .env)
    "library_music_path": "",
    "library_videos_path": "",
    # Metadados de áudio
    "write_audio_metadata": False,
    "embed_cover_in_audio": False,
    # Enrichment / AI
    "enrichment_enabled": False,
    "enrichment_batch_size": 10,
    "enrichment_interval": 300,
    "enrichment_retry_after_hours": 24,
    "ai_provider": "ollama",
    "ai_model": "llama3.1:8b",
    "ai_api_key": "",
    "ai_base_url": "http://ollama:11434",
    "ai_fallback_provider": "",
    "ai_fallback_model": "",
    "ai_fallback_api_key": "",
    "ai_fallback_base_url": "",
    # Parâmetros globais do modelo (máximos por padrão)
    "ai_num_ctx": 131072,  # 128K - janela de contexto Ollama
    "ai_num_predict": 8192,  # max tokens saída Ollama
    "ai_max_tokens": 8192,  # max tokens saída OpenRouter/OpenAI
    "ai_temperature": 0.4,  # temperatura padrão global
    # System prompts por funcionalidade (override do default). Chave = prompt_id.
    "ai_prompts": {},
}

# Chaves que contêm segredos (mascarar no GET público)
_SENSITIVE_KEYS = {
    "plex_token", "jellyfin_api_key", "tmdb_api_key",
    "lastfm_api_key", "spotify_client_secret",
    "ai_api_key", "ai_fallback_api_key",
}


class SettingsRepositoryPostgres:
    """CRUD para app_settings (chave-valor JSONB)."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def get_all(self, mask_sensitive: bool = False) -> dict[str, Any]:
        """Retorna todas as settings (defaults + overrides do DB)."""
        result = dict(SETTINGS_DEFAULTS)
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT key, value FROM app_settings")
                for row in cur.fetchall():
                    k = row["key"]
                    v = row["value"]
                    if isinstance(v, str):
                        try:
                            v = json.loads(v)
                        except (ValueError, TypeError):
                            pass
                    result[k] = v
        if mask_sensitive:
            for k in _SENSITIVE_KEYS:
                val = result.get(k, "")
                if isinstance(val, str) and val:
                    if len(val) > 4:
                        result[k] = val[:2] + "*" * (len(val) - 4) + val[-2:]
                    else:
                        result[k] = "****"
        return result

    def get(self, key: str) -> Any:
        """Retorna o valor de uma chave (override do DB ou default)."""
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM app_settings WHERE key = %s", (key,))
                row = cur.fetchone()
        if row:
            v = row["value"]
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except (ValueError, TypeError):
                    return v
            return v
        return SETTINGS_DEFAULTS.get(key)

    def set(self, key: str, value: Any) -> None:
        """Salva ou atualiza uma chave."""
        v = json.dumps(value)
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO app_settings (key, value, updated_at)
                       VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP)
                       ON CONFLICT (key) DO UPDATE SET
                         value = EXCLUDED.value,
                         updated_at = CURRENT_TIMESTAMP""",
                    (key, v),
                )
                conn.commit()

    def set_many(self, updates: dict[str, Any]) -> None:
        """Salva múltiplas chaves de uma vez. Ignora chaves não reconhecidas."""
        if not updates:
            return
        allowed = set(SETTINGS_DEFAULTS.keys())
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                for key, value in updates.items():
                    if key not in allowed:
                        continue
                    v = json.dumps(value)
                    cur.execute(
                        """INSERT INTO app_settings (key, value, updated_at)
                           VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP)
                           ON CONFLICT (key) DO UPDATE SET
                             value = EXCLUDED.value,
                             updated_at = CURRENT_TIMESTAMP""",
                        (key, v),
                    )
                conn.commit()

    def delete(self, key: str) -> bool:
        """Remove override (volta ao default do .env)."""
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM app_settings WHERE key = %s", (key,))
                conn.commit()
                return cur.rowcount > 0
