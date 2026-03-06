"""Repositório de rádio (sintonias e regras). PostgreSQL."""

from __future__ import annotations

import json

from ..db_postgres import connection_postgres


def _database_url() -> str:
    from ..config import get_settings
    url = (get_settings().database_url or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL é obrigatório para rádio.")
    return url


def _ensure_radio_tables(conn) -> None:
    """Cria tabelas de rádio se não existirem (útil quando o schema principal foi aplicado antes de incluir rádio)."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS radio_sintonias (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS radio_sintonia_rules (
                id SERIAL PRIMARY KEY,
                sintonia_id INTEGER NOT NULL REFERENCES radio_sintonias(id) ON DELETE CASCADE,
                kind TEXT NOT NULL CHECK (kind IN ('include', 'exclude')),
                "type" TEXT NOT NULL CHECK ("type" IN ('content_type', 'genre', 'artist', 'tag', 'item')),
                value TEXT NOT NULL
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_radio_sintonia_rules_sintonia_id ON radio_sintonia_rules(sintonia_id)"
        )
    conn.commit()


def list_sintonias() -> list[dict]:
    with connection_postgres(_database_url()) as conn:
        _ensure_radio_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, created_at, cover_path FROM radio_sintonias ORDER BY created_at DESC"
            )
            return [dict(r) for r in cur.fetchall()]


def get_sintonia(sintonia_id: int) -> dict | None:
    with connection_postgres(_database_url()) as conn:
        _ensure_radio_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, created_at, cover_path FROM radio_sintonias WHERE id = %s",
                (sintonia_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            out = dict(row)
            cur.execute(
                'SELECT kind, "type", value FROM radio_sintonia_rules WHERE sintonia_id = %s',
                (sintonia_id,),
            )
            rules = [dict(r) for r in cur.fetchall()]
            out["rules"] = rules
            return out


def create_sintonia(name: str, rules: list[dict]) -> int:
    """rules: list of {kind: 'include'|'exclude', type: str, value: str}."""
    with connection_postgres(_database_url()) as conn:
        _ensure_radio_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO radio_sintonias (name) VALUES (%s) RETURNING id",
                (name.strip(),),
            )
            row = cur.fetchone()
            sintonia_id = row["id"]
            for r in rules:
                kind = (r.get("kind") or "include").lower()
                type_ = (r.get("type") or "content_type").lower()
                value = r.get("value")
                if value is None:
                    value = ""
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                else:
                    value = str(value)
                cur.execute(
                    'INSERT INTO radio_sintonia_rules (sintonia_id, kind, "type", value) VALUES (%s, %s, %s, %s)',
                    (sintonia_id, kind, type_, value),
                )
            conn.commit()
            return sintonia_id


def update_sintonia(sintonia_id: int, name: str | None = None, rules: list[dict] | None = None, cover_path: str | None = None) -> bool:
    with connection_postgres(_database_url()) as conn:
        _ensure_radio_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM radio_sintonias WHERE id = %s", (sintonia_id,))
            if not cur.fetchone():
                return False
            if name is not None:
                cur.execute("UPDATE radio_sintonias SET name = %s WHERE id = %s", (name.strip(), sintonia_id))
            if cover_path is not None:
                cur.execute("UPDATE radio_sintonias SET cover_path = %s WHERE id = %s", (cover_path or "", sintonia_id))
            if rules is not None:
                cur.execute("DELETE FROM radio_sintonia_rules WHERE sintonia_id = %s", (sintonia_id,))
                for r in rules:
                    kind = (r.get("kind") or "include").lower()
                    type_ = (r.get("type") or "content_type").lower()
                    value = r.get("value")
                    if value is None:
                        value = ""
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    else:
                        value = str(value)
                    cur.execute(
                        'INSERT INTO radio_sintonia_rules (sintonia_id, kind, "type", value) VALUES (%s, %s, %s, %s)',
                        (sintonia_id, kind, type_, value),
                    )
            conn.commit()
            return True


def delete_sintonia(sintonia_id: int) -> bool:
    with connection_postgres(_database_url()) as conn:
        _ensure_radio_tables(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM radio_sintonias WHERE id = %s", (sintonia_id,))
            deleted = cur.rowcount
            conn.commit()
            return deleted > 0
