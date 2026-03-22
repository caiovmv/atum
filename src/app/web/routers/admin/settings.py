"""Admin: configurações de plataforma (system-level)."""

from fastapi import APIRouter
from pydantic import BaseModel

from ...auth_service import AuthUser, require_backoffice

router = APIRouter(prefix="/platform-settings")


class PlatformSettingsPatch(BaseModel):
    registration_open: bool | None = None
    maintenance_mode: bool | None = None
    hls_strategy: str | None = None
    hls_auto_categories: str | None = None
    hls_lru_max_gb: float | None = None
    cold_tier_days: int | None = None
    storage_pressure_pct: int | None = None
    cloud_sync_hours: str | None = None
    prefetch_count: int | None = None


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("")
async def get_platform_settings(
    actor: AuthUser = require_backoffice("super_admin"),
) -> dict:
    """Retorna configurações de plataforma da tabela app_settings."""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT key, value FROM app_settings
                   WHERE key IN (
                       'registration_open', 'maintenance_mode',
                       'hls_strategy', 'hls_auto_categories', 'hls_lru_max_gb',
                       'cold_tier_days', 'storage_pressure_pct',
                       'cloud_sync_hours', 'prefetch_count'
                   )"""
            )
            rows = await cur.fetchall()

    return {r[0]: r[1] for r in rows}


@router.patch("")
async def patch_platform_settings(
    body: PlatformSettingsPatch,
    actor: AuthUser = require_backoffice("super_admin"),
) -> dict:
    """Atualiza configurações de plataforma na tabela app_settings."""
    updates = {k: str(v) for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        return {"updated": 0}

    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            for key, value in updates.items():
                await cur.execute(
                    """INSERT INTO app_settings (key, value)
                       VALUES (%s, %s)
                       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
                    (key, value),
                )

    return {"updated": len(updates)}
