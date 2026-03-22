"""Admin: gerenciamento de convites de plataforma."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...auth_service import AuthUser, require_backoffice

router = APIRouter(prefix="/invites")


class InviteCreateRequest(BaseModel):
    family_id: str | None = None
    plan_id: str | None = None
    max_uses: int = 1
    expires_in_days: int | None = None


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("")
async def list_invites(
    actor: AuthUser = require_backoffice("super_admin", "support"),
) -> list[dict]:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT ic.id, ic.code, ic.max_uses, ic.uses_count,
                          ic.expires_at, ic.created_at,
                          u.email AS created_by_email,
                          f.name AS family_name,
                          p.code AS plan_code
                   FROM invite_codes ic
                   JOIN users u ON u.id = ic.created_by
                   LEFT JOIN families f ON f.id = ic.family_id
                   LEFT JOIN plans p ON p.id = ic.plan_id
                   ORDER BY ic.created_at DESC"""
            )
            rows = await cur.fetchall()

    cols = ["id", "code", "max_uses", "uses_count", "expires_at", "created_at",
            "created_by_email", "family_name", "plan_code"]
    return [dict(zip(cols, r)) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreateRequest,
    actor: AuthUser = require_backoffice("super_admin", "support"),
) -> dict:
    pool = await _get_pool()
    code = secrets.token_urlsafe(12)
    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            invite_id = str(uuid.uuid4())
            await cur.execute(
                """INSERT INTO invite_codes
                   (id, code, created_by, family_id, plan_id, max_uses, expires_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (invite_id, code, actor.id, body.family_id, body.plan_id,
                 body.max_uses, expires_at),
            )

    return {"id": invite_id, "code": code, "expires_at": expires_at}


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invite(
    invite_id: str,
    actor: AuthUser = require_backoffice("super_admin", "support"),
) -> None:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM invite_codes WHERE id = %s RETURNING id", (invite_id,)
            )
            if not await cur.fetchone():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Convite não encontrado")
