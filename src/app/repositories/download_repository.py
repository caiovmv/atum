"""Repositório de downloads (fila em background). Apenas PostgreSQL (DATABASE_URL obrigatório)."""

from __future__ import annotations

from ..config import get_settings
from ..domain.ports import DownloadRepository

_repo: DownloadRepository | None = None
_postgres_singleton: DownloadRepository | None = None


def get_repo() -> DownloadRepository:
    """Retorna o repositório de downloads (injetado ou singleton Postgres). Requer DATABASE_URL."""
    global _postgres_singleton
    if _repo is not None:
        return _repo
    database_url = (get_settings().database_url or "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL é obrigatório. Configure a variável de ambiente.")
    if _postgres_singleton is None:
        from .download_repository_postgres import PostgresDownloadRepository
        _postgres_singleton = PostgresDownloadRepository(database_url)
    return _postgres_singleton


def set_repo(repo: DownloadRepository | None) -> None:
    """Injeta o repositório (para testes). None restaura o padrão."""
    global _repo
    _repo = repo
