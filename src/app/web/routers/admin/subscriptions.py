"""Admin: gerenciamento de assinaturas."""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from ...auth_service import AuthUser, require_backoffice

router = APIRouter(prefix="/subscriptions")


class SubscriptionPatchRequest(BaseModel):
    status: str | None = None
    plan_id: str | None = None
    cancel_at_period_end: bool | None = None


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("")
async def list_subscriptions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    sub_status: str | None = Query(None, alias="status"),
    plan_code: str | None = Query(None),
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> dict:
    pool = await _get_pool()
    offset = (page - 1) * per_page

    filters = ["1=1"]
    params: list = []

    if sub_status:
        filters.append("s.status = %s")
        params.append(sub_status)
    if plan_code:
        filters.append("p.code = %s")
        params.append(plan_code)

    where = " AND ".join(filters)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""SELECT s.id, s.family_id, s.status, s.billing_period,
                          s.current_period_start, s.current_period_end,
                          s.canceled_at, s.cancel_at_period_end,
                          p.code AS plan_code, p.name AS plan_name,
                          f.name AS family_name,
                          COUNT(*) OVER() AS total_count
                   FROM subscriptions s
                   JOIN plans p ON p.id = s.plan_id
                   JOIN families f ON f.id = s.family_id
                   WHERE {where}
                   ORDER BY s.created_at DESC
                   LIMIT %s OFFSET %s""",
                params + [per_page, offset],
            )
            rows = await cur.fetchall()

    total = rows[0][11] if rows else 0
    cols = ["id", "family_id", "status", "billing_period",
            "current_period_start", "current_period_end",
            "canceled_at", "cancel_at_period_end",
            "plan_code", "plan_name", "family_name"]
    return {
        "items": [dict(zip(cols, r[:11])) for r in rows],
        "total": total, "page": page, "per_page": per_page,
    }


@router.patch("/{sub_id}")
async def update_subscription(
    sub_id: str,
    body: SubscriptionPatchRequest,
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> dict:
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nenhum campo para atualizar")

    valid_statuses = {"trialing", "active", "past_due", "canceled", "paused"}
    if "status" in updates and updates["status"] not in valid_statuses:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "status inválido")

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"UPDATE subscriptions SET {set_clause}, updated_at = NOW() WHERE id = %s RETURNING id",
                list(updates.values()) + [sub_id],
            )
            if not await cur.fetchone():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Assinatura não encontrada")
    return {"updated": True}
