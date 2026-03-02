"""Testes da factory de clientes e da interface base (client/factory, client/base)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.client.base import TorrentClient
from app.client.factory import create_client_from_settings, get_client
from app.client.folder import FolderClient
from app.client.transmission import TransmissionClient
from app.client.utorrent import UTorrentClient
from app.config import Settings


class TestTorrentClientBase:
    """Interface TorrentClient é implementada pelos clientes concretos."""

    def test_folder_client_is_torrent_client(self) -> None:
        assert issubclass(FolderClient, TorrentClient)

    def test_transmission_client_is_torrent_client(self) -> None:
        assert issubclass(TransmissionClient, TorrentClient)

    def test_utorrent_client_is_torrent_client(self) -> None:
        assert issubclass(UTorrentClient, TorrentClient)


class TestGetClient:
    def test_unknown_client_raises(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            get_client("unknown")
        assert "desconhecido" in str(exc_info.value).lower() or "unknown" in str(
            exc_info.value
        ).lower()

    def test_folder_returns_folder_client(self, tmp_path: Path) -> None:
        client = get_client("folder", watch_folder=str(tmp_path))
        assert isinstance(client, FolderClient)
        assert client._folder == tmp_path.resolve()

    def test_transmission_returns_transmission_client(self) -> None:
        client = get_client(
            "transmission",
            transmission_host="192.168.1.1",
            transmission_port=9092,
        )
        assert isinstance(client, TransmissionClient)
        assert client._host == "192.168.1.1"
        assert client._port == 9092

    def test_utorrent_returns_utorrent_client(self) -> None:
        client = get_client(
            "utorrent",
            utorrent_url="http://host:9999",
            utorrent_user="user",
            utorrent_password="pass",
        )
        assert isinstance(client, UTorrentClient)
        assert client._base_url == "http://host:9999"
        assert client._auth == ("user", "pass")


class TestCreateClientFromSettings:
    def test_settings_transmission_creates_transmission_client(self) -> None:
        s = Settings.model_construct(
            client_type="transmission",
            transmission_host="localhost",
            transmission_port=9091,
        )
        client = create_client_from_settings(s)
        assert isinstance(client, TransmissionClient)
        assert client._host == "localhost"

    def test_settings_folder_creates_folder_client(self) -> None:
        s = Settings.model_construct(
            client_type="folder",
            watch_folder="./torrents",
        )
        client = create_client_from_settings(s)
        assert isinstance(client, FolderClient)

    def test_settings_utorrent_creates_utorrent_client(self) -> None:
        s = Settings.model_construct(
            client_type="utorrent",
            utorrent_url="http://localhost:8080",
        )
        client = create_client_from_settings(s)
        assert isinstance(client, UTorrentClient)
