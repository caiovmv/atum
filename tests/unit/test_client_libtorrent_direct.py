"""Testes do cliente de download direto Libtorrent (TorrentP)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.client.libtorrent_direct import LibtorrentDirectClient


class TestLibtorrentDirectClientAdd:
    def test_add_magnet_returns_true(self, tmp_path: Path) -> None:
        with patch("torrentp.TorrentDownloader"):
            c = LibtorrentDirectClient(tmp_path)
            result = c.add("magnet:?xt=urn:btih:abc")
        assert result is True
        assert len(c._magnets) == 1
        assert c._magnets[0][0] == "magnet:?xt=urn:btih:abc"

    def test_add_empty_returns_false(self, tmp_path: Path) -> None:
        with patch("torrentp.TorrentDownloader"):
            c = LibtorrentDirectClient(tmp_path)
            assert c.add("") is False
            assert c.add("   ") is False
        assert len(c._magnets) == 0

    def test_add_invalid_sets_last_error(self, tmp_path: Path) -> None:
        with patch("torrentp.TorrentDownloader"):
            c = LibtorrentDirectClient(tmp_path)
            result = c.add("http://example.com/not-a-magnet")
        assert result is False
        assert c._last_error is not None
        assert "magnet" in c._last_error.lower() or "torrent" in c._last_error.lower()

    def test_add_with_save_path_override(self, tmp_path: Path) -> None:
        with patch("torrentp.TorrentDownloader"):
            c = LibtorrentDirectClient(tmp_path)
            override = str(tmp_path / "Artist" / "Album")
            result = c.add("magnet:?xt=urn:btih:xyz", save_path_override=override)
        assert result is True
        assert c._magnets[0] == ("magnet:?xt=urn:btih:xyz", override)

    def test_add_torrent_file_extension_accepted(self, tmp_path: Path) -> None:
        with patch("torrentp.TorrentDownloader"):
            c = LibtorrentDirectClient(tmp_path)
            result = c.add("file:///path/to/file.torrent")
        assert result is True


class TestLibtorrentDirectClientInit:
    def test_creates_save_path(self, tmp_path: Path) -> None:
        with patch("torrentp.TorrentDownloader"):
            c = LibtorrentDirectClient(tmp_path)
            assert c._save_path == tmp_path.resolve()
            assert c._save_path.exists()
