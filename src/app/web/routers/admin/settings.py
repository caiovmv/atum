"""Admin: configurações de plataforma."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...auth_service import AuthUser, require_super_admin

router = APIRouter(prefix="/platform-settings")


class PlatformSettingsPatch(BaseModel):
    registration_open: bool | None = None
    hls_strategy: str | None = None
    cold_tier_days: int | None = None
    storage_pressure_pct: int | None = None
    cloud_sync_hours: str | None = None
    hls_auto_categories: str | None = None
    hls_lru_max_gb: float | None = None
    prefetch_count: int | None = None


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("")
async def get_platform_settings(
    actor: AuthUser = Depends(require_super_admin),
) -> dict:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT key, value FROM app_settings ORDER BY key")
            rows = await cur.fetchall()
    # psycopg3 desserializa JSONB automaticamente; garantimos str para a UI
    return {r[0]: (r[1] if not isinstance(r[1], str) else r[1]) for r in rows}


@router.patch("")
async def patch_platform_settings(
    body: PlatformSettingsPatch,
    actor: AuthUser = Depends(require_super_admin),
) -> dict:
    raw_updates = body.model_dump(exclude_none=True)
    if not raw_updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nenhum campo enviado")

    if "hls_strategy" in raw_updates:
        if raw_updates["hls_strategy"] not in ("on_demand", "automatic", "lru"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "hls_strategy inválida")

    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            for key, value in raw_updates.items():
                # Serializa para JSON válido (JSONB exige JSON — str Python não é JSON)
                json_value = json.dumps(value)
                await cur.execute(
                    """INSERT INTO app_settings (key, value, updated_at)
                       VALUES (%s, %s::jsonb, NOW())
                       ON CONFLICT (key) DO UPDATE
                       SET value = EXCLUDED.value, updated_at = NOW()""",
                    (key, json_value),
                )

    return {"updated": list(raw_updates.keys())}
