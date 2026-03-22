"""Admin: gerenciamento de usuários."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ...auth_service import (
    AuthUser,
    require_any_backoffice,
    require_financial,
    require_super_admin,
    require_support,
)

router = APIRouter(prefix="/users")


class UserPatchRequest(BaseModel):
    is_active: bool | None = None
    backoffice_role: str | None = None
    display_name: str | None = None


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str = Query("", description="Filtrar por email ou nome"),
    plan_code: str | None = Query(None),
    active_only: bool = Query(True),
    actor: AuthUser = Depends(require_any_backoffice),
) -> dict:
    pool = await _get_pool()
    offset = (page - 1) * per_page

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            filters = ["1=1"]
            params: list = []

            if search:
                filters.append("(u.email ILIKE %s OR u.display_name ILIKE %s)")
                params += [f"%{search}%", f"%{search}%"]
            if active_only:
                filters.append("u.is_active = TRUE")
            if plan_code:
                filters.append("p.code = %s")
                params.append(plan_code)

            where = " AND ".join(filters)

            await cur.execute(
                f"""SELECT u.id, u.email, u.display_name, u.role, u.backoffice_role,
                          u.is_active, u.created_at, u.last_login_at,
                          p.code AS plan_code, p.name AS plan_name,
                          COUNT(*) OVER() AS total_count
                   FROM users u
                   JOIN families f ON f.id = u.family_id
                   JOIN plans p ON p.id = f.plan_id
                   WHERE {where}
                   ORDER BY u.created_at DESC
                   LIMIT %s OFFSET %s""",
                params + [per_page, offset],
            )
            rows = await cur.fetchall()

    total = rows[0][10] if rows else 0
    cols = ["id", "email", "display_name", "role", "backoffice_role",
            "is_active", "created_at", "last_login_at", "plan_code", "plan_name"]
    return {
        "items": [dict(zip(cols, r[:10])) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    actor: AuthUser = Depends(require_any_backoffice),
) -> dict:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT u.id, u.email, u.display_name, u.role, u.backoffice_role,
                          u.is_active, u.email_verified, u.created_at, u.last_login_at,
                          p.code, p.name, f.id AS family_id, f.name AS family_name
                   FROM users u
                   JOIN families f ON f.id = u.family_id
                   JOIN plans p ON p.id = f.plan_id
                   WHERE u.id = %s""",
                (user_id,),
            )
            row = await cur.fetchone()

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")

    cols = ["id", "email", "display_name", "role", "backoffice_role",
            "is_active", "email_verified", "created_at", "last_login_at",
            "plan_code", "plan_name", "family_id", "family_name"]
    return dict(zip(cols, row))


@router.patch("/{user_id}")
async def patch_user(
    user_id: str,
    body: UserPatchRequest,
    actor: AuthUser = Depends(require_super_admin),
) -> dict:
    pool = await _get_pool()
    updates: dict = {}
    if body.is_active is not None:
        updates["is_active"] = body.is_active
    if body.backoffice_role is not None:
        valid = {"super_admin", "financial", "support", ""}
        if body.backoffice_role not in valid:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "backoffice_role inválido")
        updates["backoffice_role"] = body.backoffice_role or None
    if body.display_name is not None:
        updates["display_name"] = body.display_name

    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nenhum campo para atualizar")

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values())

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"UPDATE users SET {set_clause}, updated_at = NOW() WHERE id = %s RETURNING id",
                values + [user_id],
            )
            if not await cur.fetchone():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")

    return {"updated": True}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    actor: AuthUser = Depends(require_super_admin),
) -> None:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
            if not await cur.fetchone():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
