"""Fixtures compartilhadas para a suíte de testes. Repositórios usam PostgreSQL (DATABASE_URL obrigatório)."""

from __future__ import annotations

import os

import pytest


def pytest_configure(config):
    """Registra marcador para testes que requerem DATABASE_URL."""
    config.addinivalue_line(
        "markers",
        "requires_db: marca testes que precisam de DATABASE_URL (PostgreSQL)",
    )


@pytest.fixture(scope="session")
def requires_database_url():
    """Pula a sessão de testes que dependem de repositórios se DATABASE_URL não estiver definido."""
    if not (os.environ.get("DATABASE_URL") or "").strip():
        pytest.skip("DATABASE_URL não definido (PostgreSQL obrigatório)", allow_module_level=True)
