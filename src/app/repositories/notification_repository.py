"""Repositório de notificações (eventos da cronologia). Apenas PostgreSQL (DATABASE_URL obrigatório)."""

from __future__ import annotations

from ..config import get_settings


def _database_url() -> str:
    url = (get_settings().database_url or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL é obrigatório. Configure a variável de ambiente.")
    return url


def create(
    type_: str,
    title: str,
    body: str | None = None,
    payload: dict | None = None,
    db_path=None,
) -> int:
    """Insere uma notificação. Retorna o id. db_path ignorado."""
    from .notification_repository_postgres import create as _pg_create
    return _pg_create(type_, title, body, payload, _database_url())


def list_notifications(
    since_id: int | None = None,
    limit: int = 50,
    unread_only: bool = False,
    db_path=None,
) -> list[dict]:
    """Lista notificações (mais recentes primeiro). db_path ignorado."""
    from .notification_repository_postgres import list_notifications as _pg_list
    return _pg_list(_database_url(), since_id, limit, unread_only)


def get_unread_count(db_path=None) -> int:
    """Retorna a quantidade de notificações não lidas. db_path ignorado."""
    from .notification_repository_postgres import get_unread_count as _pg_count
    return _pg_count(_database_url())


def mark_read(notification_id: int, db_path=None) -> bool:
    """Marca uma notificação como lida. db_path ignorado."""
    from .notification_repository_postgres import mark_read as _pg_mark
    return _pg_mark(notification_id, _database_url())


def mark_all_read(db_path=None) -> int:
    """Marca todas como lidas. db_path ignorado."""
    from .notification_repository_postgres import mark_all_read as _pg_mark
    return _pg_mark(_database_url())


def clear_all(db_path=None) -> int:
    """Remove todas as notificações. db_path ignorado."""
    from .notification_repository_postgres import clear_all as _pg_clear
    return _pg_clear(_database_url())
