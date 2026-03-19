"""Router de Recomendações AI — sugere conteúdo para Wishlist e Feeds com base no gosto do usuário."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...db_postgres import connection_postgres

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


def _database_url() -> str:
    from ...config import get_settings
    url = (get_settings().database_url or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL é obrigatório.")
    return url


def get_user_profile(limit: int = 15) -> dict:
    """Agrega top genres, artists, moods, sub_genres e content_types da biblioteca (imports + downloads)."""
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            profile: dict = {}

            cur.execute("""
                SELECT val, COUNT(*) AS cnt FROM (
                    SELECT genre AS val FROM library_imports WHERE genre IS NOT NULL AND genre != ''
                    UNION ALL
                    SELECT genre AS val FROM downloads WHERE genre IS NOT NULL AND genre != ''
                ) t GROUP BY val ORDER BY cnt DESC LIMIT %s
            """, (limit,))
            profile["top_genres"] = [r["val"] for r in cur.fetchall()]

            cur.execute("""
                SELECT val, COUNT(*) AS cnt FROM (
                    SELECT artist AS val FROM library_imports WHERE artist IS NOT NULL AND artist != ''
                    UNION ALL
                    SELECT artist AS val FROM downloads WHERE artist IS NOT NULL AND artist != ''
                ) t GROUP BY val ORDER BY cnt DESC LIMIT %s
            """, (limit,))
            profile["top_artists"] = [r["val"] for r in cur.fetchall()]

            cur.execute("""
                SELECT val, COUNT(*) AS cnt FROM (
                    SELECT UNNEST(moods) AS val FROM library_imports WHERE moods IS NOT NULL
                    UNION ALL
                    SELECT UNNEST(moods) AS val FROM downloads WHERE moods IS NOT NULL
                ) t WHERE val IS NOT NULL AND val != '' GROUP BY val ORDER BY cnt DESC LIMIT %s
            """, (limit,))
            profile["top_moods"] = [r["val"] for r in cur.fetchall()]

            cur.execute("""
                SELECT val, COUNT(*) AS cnt FROM (
                    SELECT UNNEST(sub_genres) AS val FROM library_imports WHERE sub_genres IS NOT NULL
                    UNION ALL
                    SELECT UNNEST(sub_genres) AS val FROM downloads WHERE sub_genres IS NOT NULL
                ) t WHERE val IS NOT NULL AND val != '' GROUP BY val ORDER BY cnt DESC LIMIT %s
            """, (limit,))
            profile["top_sub_genres"] = [r["val"] for r in cur.fetchall()]

            cur.execute("""
                SELECT val, COUNT(*) AS cnt FROM (
                    SELECT content_type AS val FROM library_imports WHERE content_type IS NOT NULL AND content_type != ''
                    UNION ALL
                    SELECT content_type AS val FROM downloads WHERE content_type IS NOT NULL AND content_type != ''
                ) t GROUP BY val ORDER BY cnt DESC LIMIT 5
            """)
            profile["content_types"] = [r["val"] for r in cur.fetchall()]

            cur.execute("""
                SELECT COUNT(*) AS total FROM (
                    SELECT id FROM library_imports UNION ALL SELECT id FROM downloads
                ) t
            """)
            profile["library_size"] = cur.fetchone()["total"]

            existing_artists = set(profile["top_artists"])
            cur.execute("""
                SELECT DISTINCT name FROM (
                    SELECT name FROM library_imports WHERE name IS NOT NULL
                    UNION ALL
                    SELECT name FROM downloads WHERE name IS NOT NULL
                ) t LIMIT 500
            """)
            profile["existing_names"] = [r["name"] for r in cur.fetchall()]

            return profile


class RecommendationRequest(BaseModel):
    target: str = "both"
    limit: int = 10


class RecommendationResponse(BaseModel):
    wishlist_suggestions: list[dict]
    feed_suggestions: list[dict]
    profile_summary: dict


@router.post("/recommendations")
async def ai_recommendations(body: RecommendationRequest) -> RecommendationResponse:
    """Analisa a biblioteca do usuário e sugere conteúdo para Wishlist e/ou Feeds."""
    from ...ai.llm_client import LLMClient

    client = LLMClient.from_settings()
    if not client:
        raise HTTPException(status_code=503, detail="AI não configurado.")

    try:
        profile = get_user_profile()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao coletar perfil: {e}") from e

    if profile.get("library_size", 0) == 0:
        return RecommendationResponse(
            wishlist_suggestions=[],
            feed_suggestions=[],
            profile_summary=profile,
        )

    target_instruction = ""
    if body.target == "wishlist":
        target_instruction = "Sugira SOMENTE itens para wishlist (sem feeds)."
    elif body.target == "feeds":
        target_instruction = "Sugira SOMENTE feeds RSS (sem wishlist)."
    else:
        target_instruction = f"Sugira até {body.limit} itens para wishlist E até 5 feeds RSS."

    existing_sample = ", ".join(profile.get("existing_names", [])[:30])

    user_prompt = (
        f"PERFIL DO USUÁRIO:\n"
        f"- Biblioteca: {profile.get('library_size', 0)} itens\n"
        f"- Gêneros: {', '.join(profile.get('top_genres', [])) or 'desconhecido'}\n"
        f"- Artistas frequentes: {', '.join(profile.get('top_artists', [])) or 'desconhecido'}\n"
        f"- Moods: {', '.join(profile.get('top_moods', [])) or 'desconhecido'}\n"
        f"- Sub-gêneros: {', '.join(profile.get('top_sub_genres', [])) or 'desconhecido'}\n"
        f"- Tipos de conteúdo: {', '.join(profile.get('content_types', [])) or 'música'}\n\n"
        f"JÁ NA BIBLIOTECA (amostra — NÃO repetir): {existing_sample}\n\n"
        f"{target_instruction}"
    )

    from ...ai.prompts_registry import get_prompt_temperature, get_system_prompt
    from ...deps import get_settings_repo
    repo = get_settings_repo() or {"ai_prompts": {}}
    sys_prompt = get_system_prompt("recommendations", repo)
    temp = get_prompt_temperature("recommendations", repo)
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        resp = await asyncio.to_thread(client.chat, messages, temp)
    except Exception as e:
        logger.warning("Recommendations LLM error: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro LLM: {e}") from e

    text = resp.content.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    wishlist: list[dict] = []
    feeds: list[dict] = []
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end])
            wishlist = data.get("wishlist") or []
            feeds = data.get("feeds") or []
        except (ValueError, json.JSONDecodeError):
            logger.warning("Failed to parse recommendation JSON: %s", text[:200])

    return RecommendationResponse(
        wishlist_suggestions=wishlist[:body.limit],
        feed_suggestions=feeds[:10],
        profile_summary={
            "top_genres": profile.get("top_genres", []),
            "top_artists": profile.get("top_artists", []),
            "top_moods": profile.get("top_moods", []),
            "library_size": profile.get("library_size", 0),
        },
    )
