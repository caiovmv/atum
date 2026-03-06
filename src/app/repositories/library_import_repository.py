"""Acesso ao repositório de library_imports (apenas PostgreSQL)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .library_import_repository_postgres import LibraryImportRepositoryPostgres

_singleton: "LibraryImportRepositoryPostgres | None" = None


def get_library_import_repo() -> "LibraryImportRepositoryPostgres | None":
    """Retorna o repositório de library_imports quando DATABASE_URL está definido (Postgres)."""
    global _singleton
    from ..config import get_settings
    database_url = (get_settings().database_url or "").strip()
    if not database_url:
        return None
    if _singleton is None:
        from .library_import_repository_postgres import LibraryImportRepositoryPostgres
        _singleton = LibraryImportRepositoryPostgres(database_url)
    return _singleton
