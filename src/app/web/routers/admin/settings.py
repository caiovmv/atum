"""Admin: configurações de plataforma."""

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
    return {r[0]: r[1] for r in rows}


@router.patch("")
async def patch_platform_settings(
    body: PlatformSettingsPatch,
    actor: AuthUser = Depends(require_super_admin),
) -> dict:
    updates = {k: str(v) for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nenhum campo enviado")

    if "hls_strategy" in updates:
        if updates["hls_strategy"] not in ("on_demand", "automatic", "lru"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "hls_strategy inválida")

    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            for key, value in updates.items():
                await cur.execute(
                    """INSERT INTO app_settings (key, value, updated_at)
                       VALUES (%s, %s, NOW())
                       ON CONFLICT (key) DO UPDATE
                       SET value = EXCLUDED.value, updated_at = NOW()""",
                    (key, value),
                )

    return {"updated": list(updates.keys())}
