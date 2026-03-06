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


# Nome da tabela que guarda quais migrations já foram aplicadas.
_SCHEMA_MIGRATIONS_TABLE = "schema_migrations"


def _strip_leading_comments(stmt: str) -> str:
    """Remove linhas que são só comentário do início do statement (evita pular CREATE após --)."""
    lines = stmt.strip().split("\n")
    while lines and lines[0].strip().startswith("--"):
        lines.pop(0)
    return "\n".join(lines).strip()


def _ensure_schema_postgres(conn) -> None:
    """Aplica schema principal e migrations pendentes (versionamento por scripts/migrations/)."""
    base = Path(__file__).resolve().parent.parent.parent / "scripts"
    schema_path = base / "schema_postgres.sql"
    if schema_path.is_file():
        schema_sql = schema_path.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            for stmt in schema_sql.split(";"):
                stmt = _strip_leading_comments(stmt.strip())
                if stmt:
                    cur.execute(stmt)
    migrations_dir = base / "migrations"
    if migrations_dir.is_dir():
        _run_pending_migrations(conn, migrations_dir)
    conn.commit()


def _run_pending_migrations(conn, migrations_dir: Path) -> None:
    """Cria a tabela de controle e aplica apenas migrations ainda não aplicadas."""
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {_SCHEMA_MIGRATIONS_TABLE} (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute(f"SELECT version FROM {_SCHEMA_MIGRATIONS_TABLE}")
        applied = {row["version"] for row in cur.fetchall()}
    paths = sorted(migrations_dir.glob("*.sql"))
    for path in paths:
        version = path.stem
        if version in applied:
            continue
        migration_sql = path.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            for stmt in migration_sql.split(";"):
                stmt = _strip_leading_comments(stmt.strip())
                if stmt:
                    cur.execute(stmt)
            cur.execute(
                f"INSERT INTO {_SCHEMA_MIGRATIONS_TABLE} (version) VALUES (%s)",
                (version,),
            )
        applied.add(version)
