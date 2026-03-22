"""Admin: gerenciamento de códigos promocionais."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...auth_service import AuthUser, require_financial

router = APIRouter(prefix="/promo-codes")


class PromoCodeRequest(BaseModel):
    code: str
    discount_type: str = "percent"
    discount_value: int = 0
    max_uses: int | None = None
    expires_in_days: int | None = None
    plan_code: str | None = None
    stripe_coupon_id: str | None = None


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("")
async def list_promo_codes(
    actor: AuthUser = Depends(require_financial),
) -> list[dict]:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, code, discount_type, discount_value,
                          max_uses, used_count, expires_at, is_active, created_at
                   FROM promo_codes ORDER BY created_at DESC"""
            )
            rows = await cur.fetchall()

    cols = ["id", "code", "discount_type", "discount_value",
            "max_uses", "used_count", "expires_at", "is_active", "created_at"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_promo_code(
    body: PromoCodeRequest,
    actor: AuthUser = Depends(require_financial),
) -> dict:
    if body.discount_type not in ("percent", "fixed"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "discount_type deve ser 'percent' ou 'fixed'")

    pool = await _get_pool()
    expires_sql = "NOW() + INTERVAL '1 day' * %s" if body.expires_in_days else "NULL"

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""INSERT INTO promo_codes (code, discount_type, discount_value,
                    max_uses, expires_at, stripe_coupon_id)
                    VALUES (%s, %s, %s, %s, {expires_sql}, %s)
                    RETURNING id""",
                (
                    body.code, body.discount_type, body.discount_value,
                    body.max_uses,
                    *([body.expires_in_days] if body.expires_in_days else []),
                    body.stripe_coupon_id,
                ),
            )
            row = await cur.fetchone()

    return {"id": str(row[0])}


@router.delete("/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_promo_code(
    promo_id: str,
    actor: AuthUser = Depends(require_financial),
) -> None:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE promo_codes SET is_active = FALSE WHERE id = %s RETURNING id",
                (promo_id,),
            )
            if not await cur.fetchone():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Código não encontrado")
