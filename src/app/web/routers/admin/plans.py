"""Admin: gerenciamento de planos de assinatura."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...auth_service import AuthUser, require_backoffice

router = APIRouter(prefix="/plans")


class PlanRequest(BaseModel):
    code: str | None = None
    name: str | None = None
    price_monthly_cents: int | None = None
    price_yearly_cents: int | None = None
    max_family_members: int | None = None
    max_devices_per_member: int | None = None
    base_storage_gb: int | None = None
    max_addon_storage_gb: int | None = None
    max_concurrent_downloads: int | None = None
    hls_enabled: bool | None = None
    ai_enabled: bool | None = None
    cold_tiering_enabled: bool | None = None
    trial_days: int | None = None
    stripe_product_id: str | None = None
    stripe_price_monthly_id: str | None = None
    stripe_price_yearly_id: str | None = None
    is_active: bool | None = None


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("")
async def list_plans(
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> list[dict]:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, code, name, price_monthly_cents, price_yearly_cents,
                          max_family_members, max_devices_per_member, base_storage_gb,
                          max_addon_storage_gb, max_concurrent_downloads,
                          hls_enabled, ai_enabled, cold_tiering_enabled,
                          trial_days, stripe_product_id, is_active, created_at
                   FROM plans ORDER BY price_monthly_cents ASC"""
            )
            rows = await cur.fetchall()

    cols = ["id", "code", "name", "price_monthly_cents", "price_yearly_cents",
            "max_family_members", "max_devices_per_member", "base_storage_gb",
            "max_addon_storage_gb", "max_concurrent_downloads",
            "hls_enabled", "ai_enabled", "cold_tiering_enabled",
            "trial_days", "stripe_product_id", "is_active", "created_at"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_plan(
    body: PlanRequest,
    actor: AuthUser = require_backoffice("super_admin"),
) -> dict:
    if not body.code or not body.name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "code e name são obrigatórios")

    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO plans (code, name, price_monthly_cents, price_yearly_cents,
                   max_family_members, max_devices_per_member, base_storage_gb,
                   max_addon_storage_gb, max_concurrent_downloads,
                   hls_enabled, ai_enabled, cold_tiering_enabled,
                   trial_days, stripe_product_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    body.code, body.name,
                    body.price_monthly_cents or 0, body.price_yearly_cents or 0,
                    body.max_family_members or 1, body.max_devices_per_member or 1,
                    body.base_storage_gb or 10, body.max_addon_storage_gb or 0,
                    body.max_concurrent_downloads or 1,
                    body.hls_enabled or False, body.ai_enabled or False,
                    body.cold_tiering_enabled or False,
                    body.trial_days or 0, body.stripe_product_id,
                ),
            )
            row = await cur.fetchone()
    return {"id": str(row[0])}


@router.patch("/{plan_id}")
async def update_plan(
    plan_id: str,
    body: PlanRequest,
    actor: AuthUser = require_backoffice("super_admin"),
) -> dict:
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nenhum campo para atualizar")

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"UPDATE plans SET {set_clause}, updated_at = NOW() WHERE id = %s RETURNING id",
                list(updates.values()) + [plan_id],
            )
            if not await cur.fetchone():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Plano não encontrado")
    return {"updated": True}
