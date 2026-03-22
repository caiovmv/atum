"""Admin: gerenciamento de convites de plataforma."""

import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...auth_service import AuthUser, require_support

router = APIRouter(prefix="/invites")


class InviteCreateRequest(BaseModel):
    plan_code: str = "free"
    max_uses: int = 1
    expires_in_days: int = 7


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


def _gen_code(length: int = 10) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("")
async def list_invites(
    actor: AuthUser = Depends(require_support),
) -> list[dict]:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT i.id, i.code, i.plan_code, i.max_uses, i.used_count,
                          i.expires_at, i.created_at
                   FROM invite_codes i
                   ORDER BY i.created_at DESC"""
            )
            rows = await cur.fetchall()

    cols = ["id", "code", "plan_code", "max_uses", "used_count", "expires_at", "created_at"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreateRequest,
    actor: AuthUser = Depends(require_support),
) -> dict:
    code = _gen_code()
    pool = await _get_pool()

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO invite_codes (code, plan_code, max_uses, expires_at)
                   VALUES (%s, %s, %s, NOW() + INTERVAL '1 day' * %s)
                   RETURNING id, code, expires_at""",
                (code, body.plan_code, body.max_uses, body.expires_in_days),
            )
            row = await cur.fetchone()

    return {"id": str(row[0]), "code": row[1], "expires_at": row[2]}


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invite(
    invite_id: str,
    actor: AuthUser = Depends(require_support),
) -> None:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM invite_codes WHERE id = %s RETURNING id", (invite_id,)
            )
            if not await cur.fetchone():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Convite não encontrado")
