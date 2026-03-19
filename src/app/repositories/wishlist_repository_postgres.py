"""Repositório de wishlist (PostgreSQL). Usado quando DATABASE_URL está definido."""

from __future__ import annotations

from ..db_postgres import connection_postgres

_DEFAULT_LIMIT = 5000


def add_term(term: str, database_url: str = "") -> int:
    if not term or not term.strip():
        return 0
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO wishlist (term) VALUES (%s) RETURNING id",
                (term.strip(),),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else 0


def list_all(database_url: str, *, limit: int | None = None, offset: int | None = None) -> list[dict]:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            sql = "SELECT id, term, created_at FROM wishlist ORDER BY id"
            params: list[object] = []
            effective_limit = limit if limit is not None and limit > 0 else _DEFAULT_LIMIT
            sql += " LIMIT %s"
            params.append(effective_limit)
            if offset is not None and offset > 0:
                sql += " OFFSET %s"
                params.append(offset)
            cur.execute(sql, params or None)
            return [dict(r) for r in cur.fetchall()]


def delete_by_id(wishlist_id: int, database_url: str) -> bool:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM wishlist WHERE id = %s", (wishlist_id,))
            conn.commit()
            return cur.rowcount > 0


def get_by_id(wishlist_id: int, database_url: str) -> dict | None:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, term, created_at FROM wishlist WHERE id = %s",
                (wishlist_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
