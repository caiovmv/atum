"""PostgreSQL: conexão, schema e connection pool (psycopg3, sync + async)."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool, ConnectionPool
except ImportError:
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]
    ConnectionPool = None  # type: ignore[assignment]
    AsyncConnectionPool = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_pool_lock = threading.Lock()
_pools: dict[str, ConnectionPool] = {}
_async_pools: dict[str, AsyncConnectionPool] = {}
_schema_initialized: set[str] = set()

POOL_MIN_CONN = 2
POOL_MAX_CONN = 10


def _get_pool(database_url: str) -> ConnectionPool:
    """Return (or create) a sync connection pool for the given database_url."""
    if database_url in _pools:
        return _pools[database_url]
    with _pool_lock:
        if database_url not in _pools:
            if ConnectionPool is None:
                raise RuntimeError(
                    "psycopg não instalado. Use: pip install 'psycopg[binary]' psycopg_pool"
                )
            pool = ConnectionPool(
                conninfo=database_url,
                min_size=POOL_MIN_CONN,
                max_size=POOL_MAX_CONN,
                kwargs={"row_factory": dict_row},
            )
            _pools[database_url] = pool
            logger.info("Sync connection pool criado (min=%d, max=%d)", POOL_MIN_CONN, POOL_MAX_CONN)
        return _pools[database_url]


def _ensure_schema_once(database_url: str) -> None:
    """Run schema + migrations only on first use per database_url (using sync pool)."""
    if database_url in _schema_initialized:
        return
    with _pool_lock:
        if database_url not in _schema_initialized:
            pool = _get_pool(database_url)
            with pool.connection() as conn:
                _ensure_schema_postgres(conn)
                conn.commit()
            _schema_initialized.add(database_url)


def get_connection_postgres(database_url: str):
    """Obtém conexão do pool. Compatibilidade com código legado."""
    pool = _get_pool(database_url)
    _ensure_schema_once(database_url)
    conn = pool.getconn()
    return conn


@contextmanager
def connection_postgres(database_url: str):
    """Context manager síncrono: obtém conexão do pool e devolve ao sair."""
    pool = _get_pool(database_url)
    _ensure_schema_once(database_url)
    with pool.connection() as conn:
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise


# ---------------------------------------------------------------------------
# Async pool
# ---------------------------------------------------------------------------

async def get_async_pool(database_url: str) -> AsyncConnectionPool:
    """Return (or create and open) an async connection pool."""
    if database_url in _async_pools:
        return _async_pools[database_url]
    if AsyncConnectionPool is None:
        raise RuntimeError(
            "psycopg não instalado. Use: pip install 'psycopg[binary]' psycopg_pool"
        )
    _ensure_schema_once(database_url)
    pool = AsyncConnectionPool(
        conninfo=database_url,
        min_size=POOL_MIN_CONN,
        max_size=POOL_MAX_CONN,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    await pool.open()
    _async_pools[database_url] = pool
    logger.info("Async connection pool criado (min=%d, max=%d)", POOL_MIN_CONN, POOL_MAX_CONN)
    return pool


@asynccontextmanager
async def aconnection_postgres(database_url: str):
    """Context manager assíncrono: obtém conexão do async pool e devolve ao sair."""
    pool = await get_async_pool(database_url)
    async with pool.connection() as conn:
        try:
            yield conn
        except Exception:
            await conn.rollback()
            raise


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------

def close_all_pools() -> None:
    """Fecha todos os pools síncronos. Chamar no shutdown da aplicação."""
    with _pool_lock:
        for url, pool in _pools.items():
            try:
                pool.close()
            except Exception as exc:
                logger.debug("Erro ao fechar sync pool: %s", exc)
        _pools.clear()
        _schema_initialized.clear()


async def close_all_async_pools() -> None:
    """Fecha todos os pools assíncronos. Chamar no shutdown do FastAPI."""
    for url, pool in list(_async_pools.items()):
        try:
            await pool.close()
        except Exception as exc:
            logger.debug("Erro ao fechar async pool: %s", exc)
    _async_pools.clear()


# ---------------------------------------------------------------------------
# Schema & Migrations
# ---------------------------------------------------------------------------

_SCHEMA_MIGRATIONS_TABLE = "schema_migrations"


def _strip_leading_comments(stmt: str) -> str:
    """Remove linhas que são só comentário do início do statement."""
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
