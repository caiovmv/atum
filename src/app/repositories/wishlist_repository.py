"""Repositório de wishlist (termos para busca em lote). SQLite ou PostgreSQL conforme DATABASE_URL."""

from __future__ import annotations

from pathlib import Path

from ..config import get_settings
from ..db import get_connection


def _use_postgres() -> bool:
    return bool((get_settings().database_url or "").strip())


def _conn(db_path: Path | None = None):
    return get_connection(db_path=db_path)


def add_term(term: str, db_path: Path | None = None) -> int:
    """Adiciona um termo à wishlist; retorna o id."""
    if _use_postgres():
        from .wishlist_repository_postgres import add_term as _pg_add
        return _pg_add(term, get_settings().database_url)
    if not term or not term.strip():
        return 0
    conn = _conn(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO wishlist (term) VALUES (?)",
            (term.strip(),),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def list_all(db_path: Path | None = None) -> list[dict]:
    """Lista todos os termos da wishlist (ordem de inserção)."""
    if _use_postgres():
        from .wishlist_repository_postgres import list_all as _pg_list
        return _pg_list(get_settings().database_url)
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT id, term, created_at FROM wishlist ORDER BY id",
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_by_id(wishlist_id: int, db_path: Path | None = None) -> bool:
    """Remove um termo por id; retorna True se removeu."""
    if _use_postgres():
        from .wishlist_repository_postgres import delete_by_id as _pg_del
        return _pg_del(wishlist_id, get_settings().database_url)
    conn = _conn(db_path)
    try:
        cur = conn.execute("DELETE FROM wishlist WHERE id = ?", (wishlist_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_by_id(wishlist_id: int, db_path: Path | None = None) -> dict | None:
    """Retorna um termo por id."""
    if _use_postgres():
        from .wishlist_repository_postgres import get_by_id as _pg_get
        return _pg_get(wishlist_id, get_settings().database_url)
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT id, term, created_at FROM wishlist WHERE id = ?",
            (wishlist_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
