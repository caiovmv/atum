"""Repositório de feeds (inscrições e itens processados). Apenas PostgreSQL (DATABASE_URL obrigatório)."""

from __future__ import annotations

from ..config import get_settings


def _database_url() -> str:
    url = (get_settings().database_url or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL é obrigatório. Configure a variável de ambiente.")
    return url


def add_feed_record(
    url: str,
    title: str | None = None,
    content_type: str = "music",
    db_path=None,
) -> int:
    """Insere um feed e retorna o id. db_path ignorado."""
    from .feed_repository_postgres import add_feed_record as _pg_add
    return _pg_add(url, title, content_type, _database_url())


def list_feed_records(db_path=None, conn=None) -> list[dict]:
    """Lista todos os feeds. db_path e conn ignorados."""
    from .feed_repository_postgres import list_feed_records as _pg_list
    return _pg_list(_database_url(), conn)


def is_processed(
    feed_id: int,
    entry_id: str,
    db_path=None,
    conn=None,
) -> bool:
    """conn ignorado (compatibilidade)."""
    from .feed_repository_postgres import is_processed as _pg_is
    return _pg_is(feed_id, entry_id, _database_url(), conn)


def mark_processed(
    feed_id: int,
    entry_id: str,
    entry_link: str | None = None,
    title: str | None = None,
    db_path=None,
    conn=None,
) -> None:
    """conn ignorado (compatibilidade)."""
    from .feed_repository_postgres import mark_processed as _pg_mark
    _pg_mark(feed_id, entry_id, entry_link, title, _database_url(), conn)


def get_feed_by_url(url: str, db_path=None) -> dict | None:
    from .feed_repository_postgres import get_feed_by_url as _pg_get
    return _pg_get(url, _database_url())


def get_feed_by_id(feed_id: int, db_path=None) -> dict | None:
    from .feed_repository_postgres import get_feed_by_id as _pg_get
    return _pg_get(feed_id, _database_url())


def pending_add(
    feed_id: int,
    entry_id: str,
    title: str | None,
    link: str | None,
    quality_label: str,
    db_path=None,
    conn=None,
) -> int:
    """Insere item em feed_pending. conn ignorado."""
    from .feed_repository_postgres import pending_add as _pg_add
    return _pg_add(feed_id, entry_id, title, link, quality_label, _database_url(), conn)


def pending_list(db_path=None) -> list[dict]:
    from .feed_repository_postgres import pending_list as _pg_list
    return _pg_list(_database_url())


def pending_get(pending_id: int, db_path=None) -> dict | None:
    from .feed_repository_postgres import pending_get as _pg_get
    return _pg_get(pending_id, _database_url())


def pending_delete(pending_id: int, db_path=None) -> bool:
    from .feed_repository_postgres import pending_delete as _pg_del
    return _pg_del(pending_id, _database_url())


def delete_feed_record(feed_id: int, db_path=None) -> bool:
    from .feed_repository_postgres import delete_feed_record as _pg_del
    return _pg_del(feed_id, _database_url())
