"""Admin: relatórios financeiros — MRR, ARR, churn, receita por período."""

from datetime import date, timedelta

from fastapi import APIRouter, Query

from ...auth_service import AuthUser, require_backoffice

router = APIRouter(prefix="/financial")


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("/overview")
async def financial_overview(
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> dict:
    """MRR, ARR, total de assinantes ativos por plano, churn do último mês."""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # MRR: soma de price_monthly_cents das assinaturas ativas
            await cur.execute(
                """SELECT
                     COALESCE(SUM(CASE WHEN s.billing_period = 'monthly'
                                       THEN p.price_monthly_cents
                                       ELSE p.price_yearly_cents / 12
                                  END), 0) AS mrr_cents,
                     COUNT(*) FILTER (WHERE s.status = 'active') AS active_count,
                     COUNT(*) FILTER (WHERE s.status = 'trialing') AS trialing_count
                   FROM subscriptions s
                   JOIN plans p ON p.id = s.plan_id
                   WHERE s.status IN ('active', 'trialing')"""
            )
            row = await cur.fetchone()
            mrr_cents, active_count, trialing_count = row

            # Assinantes por plano
            await cur.execute(
                """SELECT p.code, p.name, COUNT(s.id) AS count
                   FROM subscriptions s
                   JOIN plans p ON p.id = s.plan_id
                   WHERE s.status IN ('active', 'trialing')
                   GROUP BY p.id, p.code, p.name
                   ORDER BY count DESC"""
            )
            by_plan = [{"code": r[0], "name": r[1], "count": r[2]} for r in await cur.fetchall()]

            # Churn do último mês
            await cur.execute(
                """SELECT COUNT(*) FROM subscriptions
                   WHERE status = 'canceled'
                     AND canceled_at >= NOW() - INTERVAL '30 days'"""
            )
            churn_row = await cur.fetchone()
            churn_count = churn_row[0] if churn_row else 0

            # Novos assinantes do último mês
            await cur.execute(
                """SELECT COUNT(*) FROM subscriptions
                   WHERE status IN ('active', 'trialing')
                     AND created_at >= NOW() - INTERVAL '30 days'"""
            )
            new_row = await cur.fetchone()
            new_count = new_row[0] if new_row else 0

            # Receita do mês atual
            await cur.execute(
                """SELECT COALESCE(SUM(amount_cents), 0)
                   FROM payments
                   WHERE status = 'succeeded'
                     AND paid_at >= date_trunc('month', NOW())"""
            )
            rev_row = await cur.fetchone()
            month_revenue_cents = rev_row[0] if rev_row else 0

    return {
        "mrr_cents": mrr_cents,
        "mrr_brl": mrr_cents / 100,
        "arr_cents": mrr_cents * 12,
        "arr_brl": mrr_cents * 12 / 100,
        "active_subscriptions": active_count,
        "trialing_subscriptions": trialing_count,
        "churn_last_30d": churn_count,
        "new_last_30d": new_count,
        "month_revenue_cents": month_revenue_cents,
        "month_revenue_brl": month_revenue_cents / 100,
        "by_plan": by_plan,
    }


@router.get("/revenue")
async def revenue_chart(
    days: int = Query(30, ge=7, le=365, description="Número de dias para o gráfico"),
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> list[dict]:
    """Receita diária para gráfico de linhas."""
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT DATE(paid_at) AS day, SUM(amount_cents) AS total_cents
                   FROM payments
                   WHERE status = 'succeeded'
                     AND paid_at >= NOW() - INTERVAL '%s days'
                   GROUP BY DATE(paid_at)
                   ORDER BY day ASC""",
                (days,),
            )
            rows = await cur.fetchall()

    return [{"date": str(r[0]), "amount_cents": r[1], "amount_brl": r[1] / 100} for r in rows]


@router.get("/payments")
async def payment_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    pay_status: str | None = Query(None, alias="status"),
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> dict:
    """Histórico de pagamentos com paginação."""
    pool = await _get_pool()
    offset = (page - 1) * per_page

    filters = ["1=1"]
    params: list = []
    if pay_status:
        filters.append("p.status = %s")
        params.append(pay_status)

    where = " AND ".join(filters)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""SELECT p.id, p.family_id, p.amount_cents, p.currency,
                          p.status, p.description, p.paid_at, p.refunded_at,
                          p.refund_amount_cents, p.created_at,
                          u.email AS owner_email,
                          COUNT(*) OVER() AS total_count
                   FROM payments p
                   JOIN subscriptions s ON s.id = p.subscription_id
                   JOIN users u ON u.family_id = p.family_id AND u.role = 'owner'
                   WHERE {where}
                   ORDER BY p.created_at DESC
                   LIMIT %s OFFSET %s""",
                params + [per_page, offset],
            )
            rows = await cur.fetchall()

    total = rows[0][11] if rows else 0
    cols = ["id", "family_id", "amount_cents", "currency", "status",
            "description", "paid_at", "refunded_at", "refund_amount_cents",
            "created_at", "owner_email"]
    return {
        "items": [dict(zip(cols, r[:11])) for r in rows],
        "total": total, "page": page, "per_page": per_page,
    }
