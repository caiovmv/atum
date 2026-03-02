"""Repositório de histórico de buscas (PostgreSQL). Usado quando DATABASE_URL está definido."""

from __future__ import annotations

from ..db_postgres import connection_postgres


def add_query(query: str, database_url: str = "") -> int:
    if not query or not query.strip():
        return 0
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO search_history (query) VALUES (%s) RETURNING id",
                (query.strip(),),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else 0


def list_recent(limit: int = 50, database_url: str = "") -> list[dict]:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, query, created_at FROM search_history ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_by_id(history_id: int, database_url: str) -> dict | None:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, query, created_at FROM search_history WHERE id = %s",
                (history_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def prune(max_entries: int = 500, database_url: str = "") -> int:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM search_history
                   WHERE id NOT IN (
                     SELECT id FROM search_history ORDER BY created_at DESC LIMIT %s
                   )""",
                (max_entries,),
            )
            deleted = cur.rowcount
            conn.commit()
            return deleted
