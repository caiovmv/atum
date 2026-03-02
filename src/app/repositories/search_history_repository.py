"""Repositório de histórico de buscas. SQLite ou PostgreSQL conforme DATABASE_URL."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..config import get_settings
from ..db import get_connection


def _use_postgres() -> bool:
    return bool((get_settings().database_url or "").strip())


def _conn(db_path: Path | None = None):
    return get_connection(db_path=db_path)


def add_query(query: str, db_path: Path | None = None) -> int:
    """Registra uma busca e retorna o id."""
    if _use_postgres():
        from .search_history_repository_postgres import add_query as _pg_add
        return _pg_add(query, get_settings().database_url)
    if not query or not query.strip():
        return 0
    conn = _conn(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO search_history (query) VALUES (?)",
            (query.strip(),),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def list_recent(limit: int = 50, db_path: Path | None = None) -> list[dict]:
    """Lista as últimas N buscas (mais recente primeiro)."""
    if _use_postgres():
        from .search_history_repository_postgres import list_recent as _pg_list
        return _pg_list(limit, get_settings().database_url)
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT id, query, created_at FROM search_history ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_by_id(history_id: int, db_path: Path | None = None) -> dict | None:
    """Retorna uma entrada do histórico por id."""
    if _use_postgres():
        from .search_history_repository_postgres import get_by_id as _pg_get
        return _pg_get(history_id, get_settings().database_url)
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT id, query, created_at FROM search_history WHERE id = ?",
            (history_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def prune(max_entries: int = 500, db_path: Path | None = None) -> int:
    """Mantém apenas os max_entries mais recentes; retorna quantos foram removidos."""
    if _use_postgres():
        from .search_history_repository_postgres import prune as _pg_prune
        return _pg_prune(max_entries, get_settings().database_url)
    conn = _conn(db_path)
    try:
        cur = conn.execute(
            "DELETE FROM search_history WHERE id NOT IN (SELECT id FROM search_history ORDER BY created_at DESC LIMIT ?)",
            (max_entries,),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
