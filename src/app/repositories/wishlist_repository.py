"""Repositório de wishlist (termos para busca em lote). Apenas PostgreSQL (DATABASE_URL obrigatório)."""

from __future__ import annotations

from ..config import get_settings


def _database_url() -> str:
    url = (get_settings().database_url or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL é obrigatório. Configure a variável de ambiente.")
    return url


def add_term(term: str, db_path=None) -> int:
    """Adiciona um termo à wishlist; retorna o id. db_path ignorado (compatibilidade)."""
    from .wishlist_repository_postgres import add_term as _pg_add
    return _pg_add(term.strip(), _database_url()) if (term or "").strip() else 0


def list_all(db_path=None, *, limit: int | None = None, offset: int | None = None) -> list[dict]:
    """Lista todos os termos da wishlist (ordem de inserção). db_path ignorado."""
    from .wishlist_repository_postgres import list_all as _pg_list
    return _pg_list(_database_url(), limit=limit, offset=offset)


def delete_by_id(wishlist_id: int, db_path=None) -> bool:
    """Remove um termo por id; retorna True se removeu. db_path ignorado."""
    from .wishlist_repository_postgres import delete_by_id as _pg_del
    return _pg_del(wishlist_id, _database_url())


def get_by_id(wishlist_id: int, db_path=None) -> dict | None:
    """Retorna um termo por id. db_path ignorado."""
    from .wishlist_repository_postgres import get_by_id as _pg_get
    return _pg_get(wishlist_id, _database_url())
