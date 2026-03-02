"""Fixtures compartilhadas para a suíte de testes."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db_path() -> Path:
    """Path para um SQLite temporário (criado no disco para get_connection)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    import os
    os.close(fd)
    p = Path(path)
    yield p
    if p.exists():
        p.unlink(missing_ok=True)


@pytest.fixture
def db_path(temp_db_path: Path) -> Path:
    """Alias para temp_db_path (repositórios recebem db_path)."""
    return temp_db_path
