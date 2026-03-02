"""Testes do cliente uTorrent (Web API)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.client.utorrent import UTorrentClient


class TestUTorrentClientGetToken:
    def test_get_token_parses_html(self) -> None:
        client = UTorrentClient(base_url="http://localhost:8080")
        with patch.object(client, "_session") as m_sess:
            mock_resp = MagicMock()
            mock_resp.text = '<div id="token">TOKEN123</div>'
            mock_resp.raise_for_status = MagicMock()
            m_sess.get.return_value = mock_resp
            token = client._get_token()
        assert token == "TOKEN123"

    def test_get_token_returns_none_on_error(self) -> None:
        client = UTorrentClient(base_url="http://localhost:8080")
        with patch.object(client, "_session") as m_sess:
            m_sess.get.side_effect = OSError("Connection refused")
            token = client._get_token()
        assert token is None


class TestUTorrentClientAdd:
    def test_add_no_token_returns_false(self) -> None:
        client = UTorrentClient(base_url="http://localhost:8080")
        with patch.object(client, "_get_token", return_value=None):
            result = client.add("magnet:?xt=urn:btih:abc")
        assert result is False

    def test_add_magnet_success(self) -> None:
        client = UTorrentClient(base_url="http://localhost:8080")
        with patch.object(client, "_get_token", return_value="TOK"):
            with patch.object(client, "_session") as m_sess:
                mock_resp = MagicMock()
                mock_resp.raise_for_status = MagicMock()
                m_sess.get.return_value = mock_resp
                result = client.add("magnet:?xt=urn:btih:abc")
        assert result is True

    def test_add_exception_returns_false(self) -> None:
        client = UTorrentClient(base_url="http://localhost:8080")
        with patch.object(client, "_get_token", return_value="TOK"):
            with patch.object(client, "_session") as m_sess:
                m_sess.get.side_effect = OSError("Timeout")
                result = client.add("magnet:?xt=urn:btih:abc")
        assert result is False
