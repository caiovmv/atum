"""Acesso ao repositório de app_settings (apenas PostgreSQL)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .settings_repository_postgres import SettingsRepositoryPostgres

_singleton: "SettingsRepositoryPostgres | None" = None


def get_settings_repo() -> "SettingsRepositoryPostgres | None":
    """Retorna o repositório de app_settings quando DATABASE_URL está definido."""
    global _singleton
    from ..config import get_settings
    database_url = (get_settings().database_url or "").strip()
    if not database_url:
        return None
    if _singleton is None:
        from .settings_repository_postgres import SettingsRepositoryPostgres
        _singleton = SettingsRepositoryPostgres(database_url)
    return _singleton
