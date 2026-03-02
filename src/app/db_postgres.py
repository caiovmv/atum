"""PostgreSQL: conexão e schema. Usado quando DATABASE_URL está definido."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None


def get_connection_postgres(database_url: str):
    """Abre conexão com PostgreSQL. database_url ex.: postgresql://user:pass@host:5432/dbname."""
    if psycopg2 is None or RealDictCursor is None:
        raise RuntimeError("psycopg2 não instalado. Use: pip install psycopg2-binary")
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    conn.autocommit = False
    _ensure_schema_postgres(conn)
    return conn


@contextmanager
def connection_postgres(database_url: str):
    """Context manager para uma conexão PostgreSQL."""
    conn = get_connection_postgres(database_url)
    try:
        yield conn
    finally:
        conn.close()


def _ensure_schema_postgres(conn) -> None:
    """Cria tabelas se não existirem (compatível com schema SQLite)."""
    schema_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "schema_postgres.sql"
    if not schema_path.is_file():
        return
    schema_sql = schema_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        for stmt in schema_sql.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                cur.execute(stmt)
    conn.commit()
