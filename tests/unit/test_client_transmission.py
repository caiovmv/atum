"""Testes do cliente Transmission (transmission_rpc)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.client.transmission import TransmissionClient


class TestTransmissionClient:
    def test_add_success(self) -> None:
        with patch("transmission_rpc.Client") as m_client_cls:
            mock_client = MagicMock()
            m_client_cls.return_value = mock_client
            c = TransmissionClient(host="localhost", port=9091)
            result = c.add("magnet:?xt=urn:btih:abc")
            assert result is True
            mock_client.add_torrent.assert_called_once_with("magnet:?xt=urn:btih:abc")

    def test_add_with_download_dir(self) -> None:
        with patch("transmission_rpc.Client") as m_client_cls:
            mock_client = MagicMock()
            m_client_cls.return_value = mock_client
            c = TransmissionClient(
                host="localhost",
                port=9091,
                download_dir="/tmp/downloads",
            )
            c.add("magnet:?xt=urn:btih:xyz")
            mock_client.add_torrent.assert_called_once_with(
                "magnet:?xt=urn:btih:xyz",
                download_dir="/tmp/downloads",
            )

    def test_add_exception_returns_false(self) -> None:
        with patch("transmission_rpc.Client") as m_client_cls:
            m_client_cls.return_value.add_torrent.side_effect = OSError(
                "Connection refused"
            )
            c = TransmissionClient(host="invalid", port=9091)
            result = c.add("magnet:?xt=urn:btih:abc")
            assert result is False
