"""Testes do cliente Folder (salvar magnets em arquivo)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.client.folder import FolderClient


def test_folder_client_add_appends_magnet(tmp_path: Path) -> None:
    client = FolderClient(tmp_path)
    assert client.add("magnet:?xt=urn:btih:abc") is True
    assert client.add("magnet:?xt=urn:btih:def") is True
    magnets_file = tmp_path / "magnets.txt"
    assert magnets_file.exists()
    lines = magnets_file.read_text(encoding="utf-8").strip().split("\n")
    assert lines == ["magnet:?xt=urn:btih:abc", "magnet:?xt=urn:btih:def"]


def test_folder_client_add_empty_returns_false(tmp_path: Path) -> None:
    client = FolderClient(tmp_path)
    assert client.add("") is False
    assert client.add("   ") is False
    assert not (tmp_path / "magnets.txt").exists()
