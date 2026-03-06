"""Testes do módulo de configuração (Settings, get_settings)."""

from __future__ import annotations

import pytest

from app.config import Settings, get_settings


class TestSettings:
    """Valores padrão e propriedades de Settings."""

    def test_default_client_type(self) -> None:
        s = Settings.model_construct()
        assert s.client_type == "transmission"

    def test_default_transmission(self) -> None:
        s = Settings.model_construct()
        assert s.transmission_host == "localhost"
        assert s.transmission_port == 9091
        assert s.transmission_user == ""
        assert s.transmission_password == ""

    def test_default_utorrent(self) -> None:
        s = Settings.model_construct()
        assert s.utorrent_url == "http://localhost:8080"
        assert s.utorrent_user == "admin"
        assert s.utorrent_password == ""

    def test_default_indexers_base_urls(self) -> None:
        s = Settings.model_construct()
        assert s.x1337_base_url == "https://www.1377x.to"
        assert s.tpb_base_url == "https://tpb.party"
        assert s.yts_base_url == "https://yts.lt"
        assert s.limetorrents_base_url == "https://www.limetorrents.lol"

    def test_default_watch_folder_and_download_dir(self) -> None:
        s = Settings.model_construct()
        assert s.watch_folder == "./torrents"
        assert s.download_dir == ""

    def test_default_notify(self) -> None:
        s = Settings.model_construct()
        assert s.notify_enabled is False
        assert s.notify_webhook_url == ""
        assert s.notify_desktop is False

    def test_watch_folder_path_resolves(self) -> None:
        s = Settings.model_construct(watch_folder="~/torrents")
        p = s.watch_folder_path
        assert p.is_absolute()
        assert "torrents" in str(p).lower()

    def test_watch_folder_path_with_relative(self) -> None:
        s = Settings.model_construct(watch_folder="./torrents")
        p = s.watch_folder_path
        assert str(p).endswith("torrents") or "torrents" in str(p)


def test_get_settings_returns_settings() -> None:
    """get_settings() retorna uma instância de Settings."""
    s = get_settings()
    assert isinstance(s, Settings)
    assert hasattr(s, "client_type")
    assert hasattr(s, "watch_folder_path")
