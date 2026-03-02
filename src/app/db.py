"""SQLite: conexão e schema. Repositórios em app.repositories."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


def _db_path() -> Path:
    from .config import get_settings

    base = Path.home() / ".dl-torrent"
    base.mkdir(parents=True, exist_ok=True)
    return base / "feeds.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Abre conexão com o DB. db_path=None usa o path padrão (~/.dl-torrent/feeds.db)."""
    path = db_path if db_path is not None else _db_path()
    conn = sqlite3.connect(str(path), timeout=20.0)
    conn.row_factory = sqlite3.Row
    # Evitar "database is locked" com vários processos (watch + workers): esperar até 15s e usar WAL
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA journal_mode = WAL")
    _ensure_schema(conn)
    return conn


@contextmanager
def connection(db_path: Path | None = None):
    """Context manager: uma conexão por bloco (ex.: uma por poll_feeds)."""
    conn = get_connection(db_path=db_path)
    try:
        yield conn
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS feed_processed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            entry_id TEXT NOT NULL,
            entry_link TEXT,
            title TEXT,
            added_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (feed_id) REFERENCES feeds(id),
            UNIQUE(feed_id, entry_id)
        );
        CREATE INDEX IF NOT EXISTS ix_feed_processed_feed_id ON feed_processed(feed_id);

        CREATE TABLE IF NOT EXISTS feed_pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            entry_id TEXT NOT NULL,
            title TEXT,
            link TEXT,
            quality_label TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (feed_id) REFERENCES feeds(id),
            UNIQUE(feed_id, entry_id)
        );
        CREATE INDEX IF NOT EXISTS ix_feed_pending_feed_id ON feed_pending(feed_id);

        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            magnet TEXT NOT NULL,
            name TEXT,
            save_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            progress REAL DEFAULT 0,
            pid INTEGER,
            error_message TEXT,
            added_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS ix_downloads_status ON downloads(status);

        """
    )
    _migrate_downloads_columns(conn)
    _migrate_feeds_content_type(conn)
    _migrate_downloads_cover_and_metadata(conn)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS ix_search_history_created_at ON search_history(created_at DESC);

        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)


def _migrate_downloads_columns(conn: sqlite3.Connection) -> None:
    """Adiciona colunas de progresso (se/le, velocidade, tamanho, ETA) e content_path se não existirem."""
    cur = conn.execute("PRAGMA table_info(downloads)")
    existing = {row[1] for row in cur.fetchall()}
    for col, typ in [
        ("num_seeds", "INTEGER"),
        ("num_peers", "INTEGER"),
        ("download_speed_bps", "INTEGER"),
        ("total_bytes", "INTEGER"),
        ("downloaded_bytes", "INTEGER"),
        ("eta_seconds", "REAL"),
        ("content_path", "TEXT"),
        ("content_type", "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE downloads ADD COLUMN {col} {typ}")
    conn.commit()


def _migrate_feeds_content_type(conn: sqlite3.Connection) -> None:
    """Adiciona coluna content_type à tabela feeds se não existir (music, movies, tv)."""
    cur = conn.execute("PRAGMA table_info(feeds)")
    existing = {row[1] for row in cur.fetchall()}
    if "content_type" not in existing:
        conn.execute("ALTER TABLE feeds ADD COLUMN content_type TEXT DEFAULT 'music'")
        conn.commit()


def _migrate_downloads_cover_and_metadata(conn: sqlite3.Connection) -> None:
    """Adiciona colunas de capa (cover_path_small, cover_path_large) e metadados opcionais."""
    cur = conn.execute("PRAGMA table_info(downloads)")
    existing = {row[1] for row in cur.fetchall()}
    for col, typ in [
        ("cover_path_small", "TEXT"),
        ("cover_path_large", "TEXT"),
        ("year", "INTEGER"),
        ("video_quality_label", "TEXT"),
        ("audio_codec", "TEXT"),
        ("music_quality", "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE downloads ADD COLUMN {col} {typ}")
    conn.commit()


# Re-export para compatibilidade: quem importa de .db continua funcionando.
from .repositories.search_history_repository import (
    add_query as history_add_query,
    get_by_id as history_get_by_id,
    list_recent as history_list_recent,
    prune as history_prune,
)
from .repositories.wishlist_repository import (
    add_term as wishlist_add_term,
    delete_by_id as wishlist_delete_by_id,
    get_by_id as wishlist_get_by_id,
    list_all as wishlist_list_all,
)
from .repositories.feed_repository import (
    add_feed_record,
    get_feed_by_id,
    get_feed_by_url,
    is_processed,
    list_feed_records,
    mark_processed,
    pending_add,
    pending_delete,
    pending_get,
    pending_list,
)

__all__ = [
    "get_connection",
    "connection",
    "add_feed_record",
    "list_feed_records",
    "is_processed",
    "mark_processed",
    "get_feed_by_url",
    "get_feed_by_id",
    "pending_add",
    "pending_list",
    "pending_get",
    "pending_delete",
    "history_add_query",
    "history_list_recent",
    "history_get_by_id",
    "history_prune",
    "wishlist_add_term",
    "wishlist_list_all",
    "wishlist_get_by_id",
    "wishlist_delete_by_id",
]
