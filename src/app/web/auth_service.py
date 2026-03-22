"""
auth_service — autenticação JWT + bcrypt + RBAC.

Roles:
  user.role            → 'owner' | 'member'          (escopo de família)
  user.backoffice_role → 'super_admin' | 'financial' | 'support' | NULL

JWT payload:
  sub           → user.id (UUID)
  family_id     → user.family_id
  role          → user.role
  plan          → plan.code da família
  backoffice    → user.backoffice_role (omitido se NULL)
  device_id     → user_device.id
  exp / iat     → timestamps padrão JWT
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import get_settings

_log = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# ─── dataclasses leves (sem ORM) ─────────────────────────────────────────────

class AuthUser:
    """Representa o usuário autenticado extraído do JWT."""

    __slots__ = ("id", "family_id", "role", "plan", "backoffice_role", "device_id")

    def __init__(
        self,
        id: str,
        family_id: str,
        role: str,
        plan: str,
        backoffice_role: str | None,
        device_id: str,
    ) -> None:
        self.id = id
        self.family_id = family_id
        self.role = role
        self.plan = plan
        self.backoffice_role = backoffice_role
        self.device_id = device_id

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"

    @property
    def is_backoffice(self) -> bool:
        return self.backoffice_role is not None

    def has_backoffice_role(self, *roles: str) -> bool:
        return self.backoffice_role in roles


# ─── hashing de senha ─────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ─── hashing de token (para persistência segura do refresh token) ─────────────

def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


# ─── geração de tokens JWT ────────────────────────────────────────────────────

def _jwt_secret() -> str:
    secret = get_settings().jwt_secret
    if not secret:
        raise RuntimeError("JWT_SECRET não configurado — defina a variável de ambiente")
    return secret


def create_access_token(user_row: dict[str, Any], device_id: str, plan_code: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_row["id"]),
        "family_id": str(user_row["family_id"]),
        "role": user_row["role"],
        "plan": plan_code,
        "device_id": device_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expire_min),
    }
    if user_row.get("backoffice_role"):
        payload["backoffice"] = user_row["backoffice_role"]

    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def create_refresh_token(user_id: str, device_id: str) -> tuple[str, str]:
    """Retorna (raw_token, token_hash). Persiste apenas o hash no banco."""
    raw = secrets.token_urlsafe(48)
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "device_id": device_id,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_expire_days),
    }
    signed = jwt.encode(payload, _jwt_secret(), algorithm="HS256")
    return signed, hash_token(signed)


def decode_refresh_token(raw_token: str) -> dict[str, Any]:
    """Decodifica e valida um refresh token. Lança HTTPException em caso de erro."""
    try:
        payload = jwt.decode(raw_token, _jwt_secret(), algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise ValueError("not a refresh token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expirado")
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token inválido")


# ─── dependências FastAPI ─────────────────────────────────────────────────────

def _decode_access_token(raw: str) -> dict[str, Any]:
    try:
        return jwt.decode(raw, _jwt_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthUser:
    """Dependência FastAPI: extrai e valida o access token do header Authorization."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token não fornecido")

    payload = _decode_access_token(creds.credentials)

    return AuthUser(
        id=payload["sub"],
        family_id=payload["family_id"],
        role=payload["role"],
        plan=payload.get("plan", "free"),
        backoffice_role=payload.get("backoffice"),
        device_id=payload.get("device_id", ""),
    )


def require_backoffice(*allowed_roles: str):
    """
    Fábrica de dependência: exige que o usuário tenha backoffice_role em `allowed_roles`.

    Uso:
        @router.get("/admin/users")
        def list_users(user = Depends(require_backoffice("super_admin", "support"))):
            ...
    """
    def _dep(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not user.backoffice_role or user.backoffice_role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso não autorizado")
        return user
    return _dep


def require_owner(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Exige role 'owner' dentro da família."""
    if not user.is_owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Apenas o owner da família pode realizar esta ação")
    return user


# ─── seed do admin inicial ────────────────────────────────────────────────────

async def seed_admin_user(db_pool) -> None:
    """
    Cria o usuário admin inicial e sua família caso não existam.
    Deve ser chamado no lifespan da aplicação após inicializar o pool do banco.
    """
    settings = get_settings()
    if not settings.admin_email or not settings.admin_password:
        _log.debug("auth: ADMIN_EMAIL/ADMIN_PASSWORD não configurados, seed ignorado")
        return

    async with db_pool.connection() as conn:
        async with conn.cursor() as cur:
            # Verifica se já existe super_admin
            await cur.execute(
                "SELECT COUNT(*) FROM users WHERE backoffice_role = 'super_admin'"
            )
            row = await cur.fetchone()
            if row and row[0] > 0:
                return  # já existe, não criar novamente

            # Cria família admin com plano premium
            await cur.execute(
                "SELECT id FROM plans WHERE code = 'premium' LIMIT 1"
            )
            plan_row = await cur.fetchone()
            if not plan_row:
                _log.error("auth: plano 'premium' não encontrado — rode a migration 014 primeiro")
                return

            family_id = str(uuid.uuid4())
            await cur.execute(
                "INSERT INTO families (id, name, plan_id) VALUES (%s, %s, %s)",
                (family_id, "Admin Family", str(plan_row[0])),
            )

            # Cria usuário super_admin
            user_id = str(uuid.uuid4())
            await cur.execute(
                """INSERT INTO users
                   (id, email, password_hash, display_name, family_id, role, backoffice_role)
                   VALUES (%s, %s, %s, %s, %s, 'owner', 'super_admin')""",
                (
                    user_id,
                    settings.admin_email,
                    hash_password(settings.admin_password),
                    "Admin",
                    family_id,
                ),
            )

            # Cria assinatura ativa para a família admin
            await cur.execute(
                """INSERT INTO subscriptions
                   (family_id, plan_id, status, billing_period, current_period_end)
                   VALUES (%s, %s, 'active', 'yearly',
                           NOW() + INTERVAL '100 years')""",
                (family_id, str(plan_row[0])),
            )

            _log.info("auth: usuário admin criado → %s (family=%s)", settings.admin_email, family_id)
