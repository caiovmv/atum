"""Repositório de notificações (PostgreSQL)."""

from __future__ import annotations

import json

from ..db_postgres import connection_postgres


def create(
    type_: str,
    title: str,
    body: str | None = None,
    payload: dict | None = None,
    database_url: str = "",
) -> int:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO notifications (type, title, body, payload, read)
                   VALUES (%s, %s, %s, %s, FALSE) RETURNING id""",
                (type_, title, body or "", json.dumps(payload) if payload else None),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else 0


def list_notifications(
    database_url: str,
    since_id: int | None = None,
    limit: int = 50,
    unread_only: bool = False,
) -> list[dict]:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, type, title, body, payload, read, created_at
                   FROM notifications
                   WHERE (%s::bigint IS NULL OR id < %s)
                     AND (%s OR read = FALSE)
                   ORDER BY id DESC
                   LIMIT %s""",
                (since_id, since_id, not unread_only, limit),
            )
            rows = cur.fetchall()
            out = []
            for r in rows:
                d = dict(r)
                if d.get("payload") is not None and isinstance(d["payload"], str):
                    try:
                        d["payload"] = json.loads(d["payload"])
                    except Exception:
                        d["payload"] = None
                out.append(d)
            return out


def get_unread_count(database_url: str) -> int:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM notifications WHERE read = FALSE")
            row = cur.fetchone()
            return row["c"] if row else 0


def mark_read(notification_id: int, database_url: str) -> bool:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE notifications SET read = TRUE WHERE id = %s", (notification_id,))
            conn.commit()
            return cur.rowcount > 0


def mark_all_read(database_url: str) -> int:
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE notifications SET read = TRUE WHERE read = FALSE")
            conn.commit()
            return cur.rowcount


def clear_all(database_url: str) -> int:
    """Remove todas as notificações. Retorna a quantidade removida."""
    with connection_postgres(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM notifications")
            row = cur.fetchone()
            count = row["c"] if row else 0
            cur.execute("DELETE FROM notifications")
            conn.commit()
            return count
