"""Admin: relatórios financeiros."""

from fastapi import APIRouter, Depends, Query

from ...auth_service import AuthUser, require_financial

router = APIRouter(prefix="/financial")


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("/overview")
async def financial_overview(
    actor: AuthUser = Depends(require_financial),
) -> dict:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT
                     SUM(CASE WHEN s.status = 'active' AND s.billing_period = 'monthly'
                              THEN p.price_monthly_cents ELSE 0 END) AS monthly_cents,
                     SUM(CASE WHEN s.status = 'active' AND s.billing_period = 'yearly'
                              THEN p.price_yearly_cents / 12 ELSE 0 END) AS yearly_monthly_cents,
                     COUNT(CASE WHEN s.status = 'active' THEN 1 END) AS active_subscribers,
                     COUNT(CASE WHEN s.status = 'canceled' AND
                                     s.updated_at > NOW() - INTERVAL '30 days' THEN 1 END) AS churn_30d
                   FROM subscriptions s
                   JOIN plans p ON p.id = s.plan_id"""
            )
            row = await cur.fetchone()

            await cur.execute(
                """SELECT p.name, p.code, COUNT(s.id) AS subscribers
                   FROM subscriptions s
                   JOIN plans p ON p.id = s.plan_id
                   WHERE s.status = 'active'
                   GROUP BY p.id ORDER BY subscribers DESC"""
            )
            plan_rows = await cur.fetchall()

    mrr = ((row[0] or 0) + (row[1] or 0)) // 100 if row else 0
    return {
        "mrr_cents": (row[0] or 0) + (row[1] or 0),
        "mrr": mrr,
        "arr": mrr * 12,
        "active_subscribers": row[2] or 0,
        "churn_30d": row[3] or 0,
        "by_plan": [{"name": r[0], "code": r[1], "subscribers": r[2]} for r in plan_rows],
    }


@router.get("/revenue")
async def revenue_chart(
    period: str = Query("monthly", description="daily | monthly"),
    months: int = Query(6, ge=1, le=24),
    actor: AuthUser = Depends(require_financial),
) -> list[dict]:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if period == "daily":
                await cur.execute(
                    """SELECT DATE(paid_at) AS day, SUM(amount_cents) AS total
                       FROM payments WHERE status = 'succeeded'
                         AND paid_at > NOW() - INTERVAL '30 days'
                       GROUP BY day ORDER BY day"""
                )
                rows = await cur.fetchall()
                return [{"date": str(r[0]), "total_cents": r[1]} for r in rows]
            else:
                await cur.execute(
                    """SELECT TO_CHAR(DATE_TRUNC('month', paid_at), 'YYYY-MM') AS month,
                              SUM(amount_cents) AS total
                       FROM payments WHERE status = 'succeeded'
                         AND paid_at > NOW() - (INTERVAL '1 month' * %s)
                       GROUP BY month ORDER BY month""",
                    (months,),
                )
                rows = await cur.fetchall()
                return [{"month": r[0], "total_cents": r[1]} for r in rows]


@router.get("/payments")
async def payment_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    actor: AuthUser = Depends(require_financial),
) -> dict:
    pool = await _get_pool()
    offset = (page - 1) * per_page

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT py.id, py.amount_cents, py.currency, py.status,
                          py.paid_at, py.stripe_payment_intent_id,
                          f.name AS family_name, p.name AS plan_name,
                          COUNT(*) OVER() AS total_count
                   FROM payments py
                   JOIN subscriptions s ON s.id = py.subscription_id
                   JOIN families f ON f.id = s.family_id
                   JOIN plans p ON p.id = s.plan_id
                   ORDER BY py.paid_at DESC NULLS LAST
                   LIMIT %s OFFSET %s""",
                (per_page, offset),
            )
            rows = await cur.fetchall()

    total = rows[0][8] if rows else 0
    cols = ["id", "amount_cents", "currency", "status", "paid_at",
            "stripe_payment_intent_id", "family_name", "plan_name"]
    return {
        "items": [dict(zip(cols, r[:8])) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
