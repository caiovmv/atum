"""Admin: códigos promocionais."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, model_validator

from ...auth_service import AuthUser, require_backoffice

router = APIRouter(prefix="/promo-codes")


class PromoCodeRequest(BaseModel):
    code: str
    description: str | None = None
    discount_percent: int | None = None
    discount_cents: int | None = None
    max_uses: int | None = None
    applies_to_plan_id: str | None = None
    valid_until: str | None = None

    @model_validator(mode="after")
    def check_discount(self) -> "PromoCodeRequest":
        if self.discount_percent is None and self.discount_cents is None:
            raise ValueError("Informe discount_percent ou discount_cents")
        if self.discount_percent is not None and self.discount_cents is not None:
            raise ValueError("Use apenas discount_percent ou discount_cents, não os dois")
        return self


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("")
async def list_promo_codes(
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> list[dict]:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, code, description, discount_percent, discount_cents,
                          max_uses, uses_count, applies_to_plan_id,
                          valid_from, valid_until, created_at
                   FROM promo_codes ORDER BY created_at DESC"""
            )
            rows = await cur.fetchall()

    cols = ["id", "code", "description", "discount_percent", "discount_cents",
            "max_uses", "uses_count", "applies_to_plan_id",
            "valid_from", "valid_until", "created_at"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_promo_code(
    body: PromoCodeRequest,
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> dict:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO promo_codes
                   (code, description, discount_percent, discount_cents,
                    max_uses, applies_to_plan_id, valid_until)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (body.code, body.description, body.discount_percent, body.discount_cents,
                 body.max_uses, body.applies_to_plan_id, body.valid_until),
            )
            row = await cur.fetchone()
    return {"id": str(row[0])}


@router.delete("/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_promo_code(
    promo_id: str,
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> None:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM promo_codes WHERE id = %s RETURNING id", (promo_id,))
            if not await cur.fetchone():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Código não encontrado")
