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


def list_feed_records(database_url: str, conn=None) -> list[dict]:
    """Lista todos os feeds. conn ignorado (cada chamada usa sua conexão)."""
    with connection_postgres(database_url) as c:
        with c.cursor() as cur:
            cur.execute(
                """SELECT id, url, title, COALESCE(content_type, 'music') AS content_type, created_at
                   FROM feeds ORDER BY id"""
            )
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


def pending_list(database_url: str) -> list[dict]:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT p.id, p.feed_id, p.entry_id, p.title, p.link, p.quality_label, p.created_at,
                          COALESCE(f.content_type, 'music') AS content_type
                   FROM feed_pending p
                   LEFT JOIN feeds f ON p.feed_id = f.id
                   ORDER BY p.id"""
            )
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
