"""Admin: gerenciamento de assinaturas."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ...auth_service import AuthUser, require_financial

router = APIRouter(prefix="/subscriptions")


class SubscriptionPatchRequest(BaseModel):
    status: str | None = None
    cancel_at_period_end: bool | None = None


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("")
async def list_subscriptions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    sub_status: str | None = Query(None, description="active | trialing | canceled | paused"),
    actor: AuthUser = Depends(require_financial),
) -> dict:
    pool = await _get_pool()
    offset = (page - 1) * per_page

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            filters = ["1=1"]
            params: list = []

            if sub_status:
                filters.append("s.status = %s")
                params.append(sub_status)

            where = " AND ".join(filters)
            await cur.execute(
                f"""SELECT s.id, s.status, s.billing_period, s.current_period_start,
                          s.current_period_end, s.cancel_at_period_end,
                          f.name AS family_name, p.name AS plan_name, p.code AS plan_code,
                          COUNT(*) OVER() AS total_count
                   FROM subscriptions s
                   JOIN families f ON f.id = s.family_id
                   JOIN plans p ON p.id = s.plan_id
                   WHERE {where}
                   ORDER BY s.created_at DESC
                   LIMIT %s OFFSET %s""",
                params + [per_page, offset],
            )
            rows = await cur.fetchall()

    total = rows[0][9] if rows else 0
    cols = ["id", "status", "billing_period", "current_period_start",
            "current_period_end", "cancel_at_period_end",
            "family_name", "plan_name", "plan_code"]
    return {
        "items": [dict(zip(cols, r[:9])) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.patch("/{sub_id}")
async def update_subscription(
    sub_id: str,
    body: SubscriptionPatchRequest,
    actor: AuthUser = Depends(require_financial),
) -> dict:
    valid_statuses = {"active", "trialing", "canceled", "paused", "past_due", "incomplete"}
    if body.status and body.status not in valid_statuses:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Status inválido: {body.status}")

    updates: dict = {}
    if body.status is not None:
        updates["status"] = body.status
    if body.cancel_at_period_end is not None:
        updates["cancel_at_period_end"] = body.cancel_at_period_end

    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nenhum campo para atualizar")

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
