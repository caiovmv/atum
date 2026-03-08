"""
Ponto único de composição de dependências (KISS / DIP).
Expõe get_settings(), get_repo(), get_cover_cache() e permite overrides para testes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .ai.llm_client import LLMClient
    from .config import Settings
    from .domain.ports import DownloadRepository
    from .repositories.library_import_repository_postgres import LibraryImportRepositoryPostgres
    from .repositories.settings_repository_postgres import SettingsRepositoryPostgres
    from .web.cover_cache import CoverCache

_overrides: dict[str, Any] = {}


def get_settings() -> "Settings":
    """Retorna as configurações (ou override injetado em testes)."""
    if "settings" in _overrides:
        return _overrides["settings"]
    from .config import get_settings as _get
    return _get()


def get_repo() -> "DownloadRepository":
    """Retorna o repositório de downloads (ou override injetado em testes)."""
    if "repo" in _overrides:
        return _overrides["repo"]
    from .repositories.download_repository import get_repo as _get
    return _get()


def get_cover_cache() -> "CoverCache":
    """Retorna o cache de capas (ou override injetado em testes)."""
    if "cover_cache" in _overrides:
        return _overrides["cover_cache"]
    from .web.cover_cache import get_cover_cache as _get
    return _get()


def get_library_import_repo() -> "LibraryImportRepositoryPostgres | None":
    """Retorna o repositório de library_imports (Postgres) ou None se não configurado."""
    if "library_import_repo" in _overrides:
        return _overrides["library_import_repo"]
    from .repositories.library_import_repository import get_library_import_repo as _get
    return _get()


def get_settings_repo() -> "SettingsRepositoryPostgres | None":
    """Retorna o repositório de app_settings (Postgres) ou None se não configurado."""
    if "settings_repo" in _overrides:
        return _overrides["settings_repo"]
    from .repositories.settings_repository import get_settings_repo as _get
    return _get()


def get_llm_client() -> "LLMClient | None":
    """Retorna o LLM client (Ollama/OpenRouter) ou None se não configurado."""
    if "llm_client" in _overrides:
        return _overrides["llm_client"]
    from .ai.llm_client import LLMClient
    return LLMClient.from_settings()


def set_overrides(
    *,
    settings: "Settings | None" = None,
    repo: "DownloadRepository | None" = None,
    cover_cache: "CoverCache | None" = None,
) -> None:
    """Injeta dependências (para testes). None remove o override daquela dependência."""
    if settings is not None:
        _overrides["settings"] = settings
    elif "settings" in _overrides:
        del _overrides["settings"]
    if repo is not None:
        _overrides["repo"] = repo
    elif "repo" in _overrides:
        del _overrides["repo"]
    if cover_cache is not None:
        _overrides["cover_cache"] = cover_cache
    elif "cover_cache" in _overrides:
        del _overrides["cover_cache"]


def clear_overrides() -> None:
    """Remove todos os overrides (restaura padrão)."""
    _overrides.clear()
