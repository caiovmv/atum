"""Repositório de feeds (PostgreSQL). Usado quando DATABASE_URL está definido."""

from __future__ import annotations

from ..db_postgres import connection_postgres


def add_feed_record(
    url: str,
    title: str | None = None,
    content_type: str = "music",
    database_url: str = "",
) -> int:
    """Insere um feed e retorna o id. Ignora se URL já existe."""
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO feeds (url, title, content_type)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (url) DO NOTHING RETURNING id""",
                (url, title, content_type),
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                return row["id"]
            cur.execute("SELECT id FROM feeds WHERE url = %s", (url,))
            row = cur.fetchone()
            return row["id"] if row else 0


_DEFAULT_LIMIT = 5000


def list_feed_records(database_url: str, conn=None, limit: int | None = None, offset: int | None = None) -> list[dict]:
    """Lista todos os feeds. conn ignorado (cada chamada usa sua conexão)."""
    with connection_postgres(database_url) as c:
        with c.cursor() as cur:
            sql = """SELECT id, url, title, COALESCE(content_type, 'music') AS content_type, created_at
                   FROM feeds ORDER BY id"""
            params: list = []
            effective_limit = limit if limit is not None and limit > 0 else _DEFAULT_LIMIT
            sql += " LIMIT %s"
            params.append(effective_limit)
            if offset is not None and offset > 0:
                sql += " OFFSET %s"
                params.append(offset)
            cur.execute(sql, params or None)
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def is_processed(
    feed_id: int,
    entry_id: str,
    database_url: str,
    conn=None,
) -> bool:
    with connection_postgres(database_url) as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM feed_processed WHERE feed_id = %s AND entry_id = %s",
                (feed_id, entry_id),
            )
            return cur.fetchone() is not None


def is_processed_batch(
    feed_id: int,
    entry_ids: list[str],
    database_url: str,
) -> set[str]:
    """Return the subset of entry_ids already processed for a given feed."""
    if not entry_ids:
        return set()
    with connection_postgres(database_url) as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT entry_id FROM feed_processed WHERE feed_id = %s AND entry_id = ANY(%s)",
                (feed_id, entry_ids),
            )
            return {row["entry_id"] for row in cur.fetchall()}


def mark_processed(
    feed_id: int,
    entry_id: str,
    entry_link: str | None = None,
    title: str | None = None,
    database_url: str = "",
    conn=None,
) -> None:
    with connection_postgres(database_url) as c:
        with c.cursor() as cur:
            cur.execute(
                """INSERT INTO feed_processed (feed_id, entry_id, entry_link, title)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (feed_id, entry_id) DO NOTHING""",
                (feed_id, entry_id, entry_link, title),
            )
            c.commit()


def mark_processed_batch(
    items: list[tuple[int, str, str | None, str | None]],
    database_url: str = "",
) -> None:
    """Mark multiple entries as processed in a single transaction.
    items: list of (feed_id, entry_id, entry_link, title)."""
    if not items:
        return
    with connection_postgres(database_url) as c:
        with c.cursor() as cur:
            cur.executemany(
                """INSERT INTO feed_processed (feed_id, entry_id, entry_link, title)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (feed_id, entry_id) DO NOTHING""",
                items,
            )
            c.commit()


def get_feed_by_url(url: str, database_url: str) -> dict | None:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, url, title, COALESCE(content_type, 'music') AS content_type FROM feeds WHERE url = %s",
                (url,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_feed_by_id(feed_id: int, database_url: str) -> dict | None:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, url, title, COALESCE(content_type, 'music') AS content_type FROM feeds WHERE id = %s",
                (feed_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def pending_add(
    feed_id: int,
    entry_id: str,
    title: str | None,
    link: str | None,
    quality_label: str,
    database_url: str = "",
    conn=None,
) -> int:
    with connection_postgres(database_url) as c:
        with c.cursor() as cur:
            cur.execute(
                """INSERT INTO feed_pending (feed_id, entry_id, title, link, quality_label)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (feed_id, entry_id) DO NOTHING RETURNING id""",
                (feed_id, entry_id, title or "", link, quality_label or "?"),
            )
            row = cur.fetchone()
            c.commit()
            if row:
                return row["id"]
            cur.execute(
                "SELECT id FROM feed_pending WHERE feed_id = %s AND entry_id = %s",
                (feed_id, entry_id),
            )
            row = cur.fetchone()
            return row["id"] if row else 0


def pending_list(database_url: str, *, limit: int | None = None, offset: int | None = None) -> list[dict]:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            sql = """SELECT p.id, p.feed_id, p.entry_id, p.title, p.link, p.quality_label, p.created_at,
                          COALESCE(f.content_type, 'music') AS content_type
                   FROM feed_pending p
                   LEFT JOIN feeds f ON p.feed_id = f.id
                   ORDER BY p.id"""
            params: list[object] = []
            effective_limit = limit if limit is not None and limit > 0 else _DEFAULT_LIMIT
            sql += " LIMIT %s"
            params.append(effective_limit)
            if offset is not None and offset > 0:
                sql += " OFFSET %s"
                params.append(offset)
            cur.execute(sql, params or None)
            return [dict(r) for r in cur.fetchall()]


def pending_get(pending_id: int, database_url: str) -> dict | None:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, feed_id, entry_id, title, link, quality_label FROM feed_pending WHERE id = %s",
                (pending_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def pending_delete(pending_id: int, database_url: str) -> bool:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feed_pending WHERE id = %s", (pending_id,))
            conn.commit()
            return cur.rowcount > 0


def delete_feed_record(feed_id: int, database_url: str) -> bool:
    """Remove um feed e seus itens em feed_pending e feed_processed. Retorna True se existia."""
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feed_pending WHERE feed_id = %s", (feed_id,))
            cur.execute("DELETE FROM feed_processed WHERE feed_id = %s", (feed_id,))
            cur.execute("DELETE FROM feeds WHERE id = %s", (feed_id,))
            conn.commit()
            return cur.rowcount > 0
