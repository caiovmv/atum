"""
Router de autenticação — /api/auth/*

Endpoints públicos (sem JWT):
  POST /api/auth/register   → criar conta (requer invite code se registration_open=False)
  POST /api/auth/login      → login com email/senha
  POST /api/auth/refresh    → renovar access token via refresh token

Endpoints protegidos (JWT obrigatório):
  POST /api/auth/logout     → revogar refresh token atual
  GET  /api/auth/me         → dados do usuário autenticado
  GET  /api/auth/devices    → dispositivos da conta
  DELETE /api/auth/devices/{device_id}  → revogar dispositivo
  POST /api/auth/invite     → criar convite de família (owner only)
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator

from ...config import get_settings
from ..auth_service import (
    AuthUser,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    hash_password,
    hash_token,
    require_owner,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str = ""
    invite_code: str = ""

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A senha deve ter pelo menos 8 caracteres")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_name: str = "Unknown Device"


class RefreshRequest(BaseModel):
    refresh_token: str


class InviteCreateRequest(BaseModel):
    max_uses: int = 1
    expires_in_days: int | None = None


# ─── helpers de banco ─────────────────────────────────────────────────────────

async def _get_db():
    """Importação lazy do pool para evitar dependência circular."""
    from ...db import get_pool
    return get_pool()


async def _fetch_plan_code(conn, family_id: str) -> str:
    async with conn.cursor() as cur:
        await cur.execute(
            """SELECT p.code FROM plans p
               JOIN families f ON f.plan_id = p.id
               WHERE f.id = %s""",
            (family_id,),
        )
        row = await cur.fetchone()
        return row[0] if row else "free"


async def _register_device(conn, user_id: str, device_name: str, request: Request) -> str:
    device_id = str(uuid.uuid4())
    ua = request.headers.get("user-agent", "")[:500]
    ip = request.client.host if request.client else ""
    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO user_devices (id, user_id, device_name, user_agent, ip_address)
               VALUES (%s, %s, %s, %s, %s)""",
            (device_id, user_id, device_name, ua, ip),
        )
    return device_id


async def _issue_tokens(conn, user_row: dict, device_id: str) -> dict:
    """Gera access + refresh token e persiste o refresh no banco."""
    plan_code = await _fetch_plan_code(conn, str(user_row["family_id"]))
    access_token = create_access_token(user_row, device_id, plan_code)
    refresh_raw, refresh_hash = create_refresh_token(str(user_row["id"]), device_id)
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)

    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO refresh_tokens (token_hash, user_id, device_id, expires_at)
               VALUES (%s, %s, %s, %s)""",
            (refresh_hash, str(user_row["id"]), device_id, expires_at),
        )

    return {
        "access_token": access_token,
        "refresh_token": refresh_raw,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_expire_min * 60,
    }


# ─── endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request) -> dict:
    settings = get_settings()
    pool = await _get_db()

    async with pool.connection() as conn:
        async with conn.cursor() as cur:

            # Verifica se e-mail já existe
            await cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
            if await cur.fetchone():
                raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")

            family_id: str | None = None
            plan_id: str | None = None

            # Processa invite code
            if body.invite_code:
                await cur.execute(
                    """SELECT id, family_id, plan_id, max_uses, uses_count, expires_at
                       FROM invite_codes WHERE code = %s""",
                    (body.invite_code,),
                )
                invite = await cur.fetchone()
                if not invite:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Convite inválido")
                inv_id, inv_family_id, inv_plan_id, max_uses, uses_count, expires_at = invite
                if expires_at and expires_at < datetime.now(timezone.utc):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Convite expirado")
                if uses_count >= max_uses:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Convite já utilizado")

                family_id = str(inv_family_id) if inv_family_id else None
                plan_id = str(inv_plan_id) if inv_plan_id else None

                # Incrementa usos
                await cur.execute(
                    "UPDATE invite_codes SET uses_count = uses_count + 1 WHERE id = %s",
                    (inv_id,),
                )

            elif not settings.registration_open:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Registro por convite apenas. Solicite um convite ao administrador.",
                )

            # Cria família se não veio do invite
            if family_id is None:
                if not plan_id:
                    await cur.execute("SELECT id FROM plans WHERE code = 'free' LIMIT 1")
                    plan_row = await cur.fetchone()
                    plan_id = str(plan_row[0]) if plan_row else None

                family_id = str(uuid.uuid4())
                await cur.execute(
                    "INSERT INTO families (id, name, plan_id) VALUES (%s, %s, %s)",
                    (family_id, body.display_name or body.email.split("@")[0], plan_id),
                )
                # Cria assinatura free
                settings_defaults = get_settings()
                await cur.execute(
                    """INSERT INTO subscriptions
                       (family_id, plan_id, status, billing_period, current_period_end)
                       VALUES (%s, %s, 'active', 'monthly', NOW() + INTERVAL '100 years')""",
                    (family_id, plan_id),
                )
                role = "owner"
            else:
                # Entrando numa família existente via invite
                await cur.execute(
                    "SELECT COUNT(*) FROM users WHERE family_id = %s", (family_id,)
                )
                count_row = await cur.fetchone()
                role = "owner" if (count_row and count_row[0] == 0) else "member"

            # Cria usuário
            user_id = str(uuid.uuid4())
            await cur.execute(
                """INSERT INTO users
                   (id, email, password_hash, display_name, family_id, role)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    user_id,
                    body.email,
                    hash_password(body.password),
                    body.display_name or body.email.split("@")[0],
                    family_id,
                    role,
                ),
            )

        user_row = {
            "id": user_id,
            "family_id": family_id,
            "role": role,
            "backoffice_role": None,
        }
        device_id = await _register_device(conn, user_id, "Web Browser", request)
        return await _issue_tokens(conn, user_row, device_id)


@router.post("/login")
async def login(body: LoginRequest, request: Request) -> dict:
    pool = await _get_db()

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, family_id, role, backoffice_role, password_hash, is_active
                   FROM users WHERE email = %s""",
                (body.email,),
            )
            row = await cur.fetchone()

        if not row:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")

        user_id, family_id, role, backoffice_role, pw_hash, is_active = row

        if not is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Conta suspensa")

        if not verify_password(body.password, pw_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")

        user_row = {
            "id": user_id,
            "family_id": family_id,
            "role": role,
            "backoffice_role": backoffice_role,
        }

        # Atualiza last_login_at
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = %s", (str(user_id),)
            )

        device_id = await _register_device(conn, str(user_id), body.device_name, request)
        return await _issue_tokens(conn, user_row, device_id)


@router.post("/refresh")
async def refresh_token(body: RefreshRequest) -> dict:
    payload = decode_refresh_token(body.refresh_token)
    token_hash = hash_token(body.refresh_token)

    pool = await _get_db()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, user_id, device_id, expires_at, revoked_at
                   FROM refresh_tokens WHERE token_hash = %s""",
                (token_hash,),
            )
            rt_row = await cur.fetchone()

        if not rt_row:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token não encontrado")

        rt_id, user_id, device_id, expires_at, revoked_at = rt_row

        if revoked_at:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revogado")
        if expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expirado")

        # Busca dados do usuário
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, family_id, role, backoffice_role, is_active FROM users WHERE id = %s",
                (str(user_id),),
            )
            user_row_data = await cur.fetchone()

        if not user_row_data or not user_row_data[4]:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inativo")

        uid, family_id, role, backoffice_role, _ = user_row_data
        user_row = {
            "id": uid,
            "family_id": family_id,
            "role": role,
            "backoffice_role": backoffice_role,
        }

        # Rotaciona o refresh token (revoga o atual, emite novo)
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW() WHERE id = %s", (rt_id,)
            )

        return await _issue_tokens(conn, user_row, str(device_id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    token_hash = hash_token(body.refresh_token)
    pool = await _get_db()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """UPDATE refresh_tokens SET revoked_at = NOW()
                   WHERE token_hash = %s AND user_id = %s""",
                (token_hash, current_user.id),
            )


@router.get("/me")
async def me(current_user: AuthUser = Depends(get_current_user)) -> dict:
    pool = await _get_db()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT u.id, u.email, u.display_name, u.role, u.backoffice_role,
                          u.created_at, u.last_login_at,
                          p.code AS plan_code, p.name AS plan_name,
                          p.hls_enabled, p.ai_enabled, p.cold_tiering_enabled,
                          p.base_storage_gb, p.max_addon_storage_gb,
                          p.max_family_members, p.max_devices_per_member,
                          COALESCE(SUM(sa.quantity) FILTER (WHERE sa.addon_type = 'storage_gb' AND sa.active), 0) AS extra_storage_gb
                   FROM users u
                   JOIN families f ON f.id = u.family_id
                   JOIN plans p ON p.id = f.plan_id
                   LEFT JOIN storage_addons sa ON sa.family_id = u.family_id
                   WHERE u.id = %s
                   GROUP BY u.id, p.id""",
                (current_user.id,),
            )
            row = await cur.fetchone()

    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")

    cols = [
        "id", "email", "display_name", "role", "backoffice_role",
        "created_at", "last_login_at",
        "plan_code", "plan_name", "hls_enabled", "ai_enabled", "cold_tiering_enabled",
        "base_storage_gb", "max_addon_storage_gb",
        "max_family_members", "max_devices_per_member", "extra_storage_gb",
    ]
    data = dict(zip(cols, row))
    data["total_storage_gb"] = data["base_storage_gb"] + data["extra_storage_gb"]
    return data


@router.get("/devices")
async def list_devices(current_user: AuthUser = Depends(get_current_user)) -> list[dict]:
    pool = await _get_db()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, device_name, user_agent, ip_address, created_at, last_seen_at
                   FROM user_devices WHERE user_id = %s ORDER BY last_seen_at DESC""",
                (current_user.id,),
            )
            rows = await cur.fetchall()

    cols = ["id", "device_name", "user_agent", "ip_address", "created_at", "last_seen_at"]
    return [dict(zip(cols, r)) for r in rows]


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_device(
    device_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> None:
    pool = await _get_db()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # Garante que o device pertence ao usuário atual
            await cur.execute(
                "SELECT id FROM user_devices WHERE id = %s AND user_id = %s",
                (device_id, current_user.id),
            )
            if not await cur.fetchone():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Dispositivo não encontrado")

            # Revoga todos os refresh tokens deste dispositivo
            await cur.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW() WHERE device_id = %s AND revoked_at IS NULL",
                (device_id,),
            )
            await cur.execute("DELETE FROM user_devices WHERE id = %s", (device_id,))


@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreateRequest,
    current_user: AuthUser = Depends(require_owner),
) -> dict:
    """Cria convite de família. Apenas o owner pode convidar novos membros."""
    pool = await _get_db()
    code = secrets.token_urlsafe(12)
    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            invite_id = str(uuid.uuid4())
            await cur.execute(
                """INSERT INTO invite_codes
                   (id, code, created_by, family_id, max_uses, expires_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (invite_id, code, current_user.id, current_user.family_id, body.max_uses, expires_at),
            )

    return {
        "id": invite_id,
        "code": code,
        "family_id": current_user.family_id,
        "max_uses": body.max_uses,
        "expires_at": expires_at,
    }
