"""Repositório de feeds (inscrições e itens processados). SQLite ou PostgreSQL conforme DATABASE_URL."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..config import get_settings
from ..db import get_connection


def _use_postgres() -> bool:
    return bool((get_settings().database_url or "").strip())


def _conn(db_path: Path | None = None):
    return get_connection(db_path=db_path)


def _use_conn(conn: sqlite3.Connection | None, db_path: Path | None = None):
    """Se conn for passado, retorna (conn, False) para não fechar. Senão (get_connection(), True)."""
    if conn is not None:
        return conn, False
    return _conn(db_path), True


def add_feed_record(
    url: str,
    title: str | None = None,
    content_type: str = "music",
    db_path: Path | None = None,
) -> int:
    """Insere um feed e retorna o id. Ignora se URL já existe. content_type: music, movies, tv."""
    if _use_postgres():
        from .feed_repository_postgres import add_feed_record as _pg_add
        return _pg_add(url, title, content_type, get_settings().database_url)
    conn = _conn(db_path)
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO feeds (url, title, content_type) VALUES (?, ?, ?)",
            (url, title, content_type),
        )
        conn.commit()
        if cur.lastrowid and cur.lastrowid > 0:
            return cur.lastrowid
        row = conn.execute("SELECT id FROM feeds WHERE url = ?", (url,)).fetchone()
        return row["id"] if row else 0
    finally:
        conn.close()


def list_feed_records(
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    """Lista todos os feeds (id, url, title, content_type). conn opcional para reutilizar (ex.: poll em lote)."""
    if _use_postgres():
        from .feed_repository_postgres import list_feed_records as _pg_list
        return _pg_list(get_settings().database_url, conn)
    c, should_close = _use_conn(conn, db_path)
    try:
        rows = c.execute(
            "SELECT id, url, title, COALESCE(content_type, 'music') AS content_type, created_at FROM feeds ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if should_close:
            c.close()


def is_processed(
    feed_id: int,
    entry_id: str,
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> bool:
    """conn opcional para reutilizar (ex.: poll em lote)."""
    if _use_postgres():
        from .feed_repository_postgres import is_processed as _pg_is
        return _pg_is(feed_id, entry_id, get_settings().database_url, conn)
    c, should_close = _use_conn(conn, db_path)
    try:
        r = c.execute(
            "SELECT 1 FROM feed_processed WHERE feed_id = ? AND entry_id = ?",
            (feed_id, entry_id),
        ).fetchone()
        return r is not None
    finally:
        if should_close:
            c.close()


def mark_processed(
    feed_id: int,
    entry_id: str,
    entry_link: str | None = None,
    title: str | None = None,
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """conn opcional para reutilizar (ex.: poll em lote)."""
    if _use_postgres():
        from .feed_repository_postgres import mark_processed as _pg_mark
        _pg_mark(feed_id, entry_id, entry_link, title, get_settings().database_url, conn)
        return
    c, should_close = _use_conn(conn, db_path)
    try:
        c.execute(
            "INSERT OR IGNORE INTO feed_processed (feed_id, entry_id, entry_link, title) VALUES (?, ?, ?, ?)",
            (feed_id, entry_id, entry_link, title),
        )
        c.commit()
    finally:
        if should_close:
            c.close()


def get_feed_by_url(url: str, db_path: Path | None = None) -> dict | None:
    if _use_postgres():
        from .feed_repository_postgres import get_feed_by_url as _pg_get
        return _pg_get(url, get_settings().database_url)
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT id, url, title, COALESCE(content_type, 'music') AS content_type FROM feeds WHERE url = ?",
            (url,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_feed_by_id(feed_id: int, db_path: Path | None = None) -> dict | None:
    if _use_postgres():
        from .feed_repository_postgres import get_feed_by_id as _pg_get
        return _pg_get(feed_id, get_settings().database_url)
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT id, url, title, COALESCE(content_type, 'music') AS content_type FROM feeds WHERE id = ?",
            (feed_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# --- Itens pendentes (novidades do poll guardadas para escolher depois) ---


def pending_add(
    feed_id: int,
    entry_id: str,
    title: str | None,
    link: str | None,
    quality_label: str,
    db_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Insere item em feed_pending. Retorna id (ou 0 se já existir por feed_id+entry_id)."""
    if _use_postgres():
        from .feed_repository_postgres import pending_add as _pg_add
        return _pg_add(feed_id, entry_id, title, link, quality_label, get_settings().database_url, conn)
    c, should_close = _use_conn(conn, db_path)
    try:
        cur = c.execute(
            "INSERT OR IGNORE INTO feed_pending (feed_id, entry_id, title, link, quality_label) VALUES (?, ?, ?, ?, ?)",
            (feed_id, entry_id, title or "", link, quality_label or "?"),
        )
        c.commit()
        if cur.lastrowid and cur.lastrowid > 0:
            return cur.lastrowid
        row = c.execute(
            "SELECT id FROM feed_pending WHERE feed_id = ? AND entry_id = ?",
            (feed_id, entry_id),
        ).fetchone()
        return row["id"] if row else 0
    finally:
        if should_close:
            c.close()


def pending_list(db_path: Path | None = None) -> list[dict]:
    """Lista todos os itens pendentes (id, feed_id, entry_id, title, link, quality_label, created_at, content_type do feed)."""
    if _use_postgres():
        from .feed_repository_postgres import pending_list as _pg_list
        return _pg_list(get_settings().database_url)
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            """SELECT p.id, p.feed_id, p.entry_id, p.title, p.link, p.quality_label, p.created_at,
                      COALESCE(f.content_type, 'music') AS content_type
               FROM feed_pending p
               LEFT JOIN feeds f ON p.feed_id = f.id
               ORDER BY p.id"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def pending_get(pending_id: int, db_path: Path | None = None) -> dict | None:
    """Retorna um item pendente por id."""
    if _use_postgres():
        from .feed_repository_postgres import pending_get as _pg_get
        return _pg_get(pending_id, get_settings().database_url)
    conn = _conn(db_path)
    try:
        row = conn.execute(
            "SELECT id, feed_id, entry_id, title, link, quality_label FROM feed_pending WHERE id = ?",
            (pending_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def pending_delete(pending_id: int, db_path: Path | None = None) -> bool:
    """Remove um item pendente. Retorna True se existia."""
    if _use_postgres():
        from .feed_repository_postgres import pending_delete as _pg_del
        return _pg_del(pending_id, get_settings().database_url)
    conn = _conn(db_path)
    try:
        cur = conn.execute("DELETE FROM feed_pending WHERE id = ?", (pending_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
