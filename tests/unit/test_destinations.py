"""Testes do módulo de destinos de magnet (destinations)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.destinations import (
    BackgroundQueueDestination,
    ClientDestination,
    DirectDownloadDestination,
    WatchFolderDestination,
    resolve_destination,
)


class TestWatchFolderDestination:
    def test_send_success(self) -> None:
        with patch("app.destinations.get_client") as m_get:
            mock_client = MagicMock()
            mock_client.add.return_value = True
            m_get.return_value = mock_client
            dest = WatchFolderDestination("/tmp/watch")
            ok, err = dest.send("magnet:?xt=urn:btih:abc", "Title")
        assert ok is True
        assert err is None
        mock_client.add.assert_called_once_with("magnet:?xt=urn:btih:abc")

    def test_send_failure(self) -> None:
        with patch("app.destinations.get_client") as m_get:
            mock_client = MagicMock()
            mock_client.add.return_value = False
            mock_client._last_error = "Permission denied"
            m_get.return_value = mock_client
            dest = WatchFolderDestination("/tmp/watch")
            ok, err = dest.send("magnet:?xt=urn:btih:abc", "Title")
        assert ok is False
        assert err == "Permission denied"

    def test_success_message(self) -> None:
        dest = WatchFolderDestination("/tmp/watch")
        assert "magnet(s) salvo(s)" in dest.success_message(2, 0)
        assert "falha(s)" in dest.success_message(2, 1)

    def test_failure_message(self) -> None:
        dest = WatchFolderDestination("/tmp/watch")
        assert "Nenhum magnet" in dest.failure_message()

    def test_run_after_if_sync_noop(self) -> None:
        dest = WatchFolderDestination("/tmp/watch")
        dest.run_after_if_sync()


class TestClientDestination:
    def test_send_success(self) -> None:
        with patch("app.client.create_client_from_settings") as m_create:
            mock_client = MagicMock()
            mock_client.add.return_value = True
            m_create.return_value = mock_client
            s = Settings.model_construct()
            dest = ClientDestination(s)
            ok, err = dest.send("magnet:?xt=urn:btih:abc", "Title")
        assert ok is True
        assert err is None

    def test_send_failure(self) -> None:
        with patch("app.client.create_client_from_settings") as m_create:
            mock_client = MagicMock()
            mock_client.add.return_value = False
            mock_client._last_error = "Connection refused"
            m_create.return_value = mock_client
            s = Settings.model_construct()
            dest = ClientDestination(s)
            ok, err = dest.send("magnet:?xt=urn:btih:abc", "Title")
        assert ok is False
        assert err == "Connection refused"

    def test_failure_message(self) -> None:
        s = Settings.model_construct()
        dest = ClientDestination(s)
        assert "Nenhum torrent" in dest.failure_message()


class TestBackgroundQueueDestination:
    def test_send_success(self) -> None:
        with patch("app.destinations.download_add") as m_add, patch(
            "app.destinations.download_start"
        ) as m_start:
            m_add.return_value = 42
            dest = BackgroundQueueDestination("/tmp/save")
            ok, err = dest.send("magnet:?xt=urn:btih:abc", "My Album")
        assert ok is True
        assert err is None
        m_add.assert_called_once()
        m_start.assert_called_once_with(42)

    def test_send_failure(self) -> None:
        with patch("app.destinations.download_add") as m_add, patch(
            "app.destinations.download_start"
        ):
            m_add.return_value = 0
            dest = BackgroundQueueDestination("/tmp/save")
            ok, err = dest.send("magnet:?xt=urn:btih:abc", "Title")
        assert ok is False
        assert err is None

    def test_send_with_organize_calls_extract(self) -> None:
        with patch("app.destinations.download_add") as m_add, patch(
            "app.destinations.download_start"
        ), patch("app.destinations.extract_subpath_by_content_type") as m_extract:
            m_extract.return_value = "Artist/Album"
            m_add.return_value = 1
            dest = BackgroundQueueDestination("/tmp/save", organize_by_artist_album=True)
            dest.send("magnet:?xt=urn:btih:abc", "Artist - Album [FLAC]")
        m_extract.assert_called_once_with("Artist - Album [FLAC]", "music")
        call_path = m_add.call_args[0][1]
        assert "Artist" in call_path
        assert "Album" in call_path

    def test_success_message(self) -> None:
        dest = BackgroundQueueDestination("/tmp/save")
        assert "background" in dest.success_message(1, 0)
        assert "falha(s)" in dest.success_message(2, 1)

    def test_failure_message(self) -> None:
        dest = BackgroundQueueDestination("/tmp/save")
        assert "Nenhum torrent" in dest.failure_message()


class TestDirectDownloadDestination:
    def test_send_success(self) -> None:
        with patch(
            "app.client.libtorrent_direct.LibtorrentDirectClient",
            MagicMock(return_value=MagicMock(add=MagicMock(return_value=True))),
        ):
            dest = DirectDownloadDestination("/tmp/direct")
            ok, err = dest.send("magnet:?xt=urn:btih:abc", "Title")
        assert ok is True
        assert err is None

    def test_send_failure(self) -> None:
        with patch(
            "app.client.libtorrent_direct.LibtorrentDirectClient",
            MagicMock(
                return_value=MagicMock(
                    add=MagicMock(return_value=False), _last_error="Invalid magnet"
                )
            ),
        ):
            dest = DirectDownloadDestination("/tmp/direct")
            ok, err = dest.send("invalid", "Title")
        assert ok is False
        assert err == "Invalid magnet"

    def test_run_after_if_sync_calls_run_until_complete(self) -> None:
        mock_client = MagicMock()
        with patch(
            "app.client.libtorrent_direct.LibtorrentDirectClient",
            MagicMock(return_value=mock_client),
        ):
            dest = DirectDownloadDestination("/tmp/direct")
            dest.run_after_if_sync(progress_callback=MagicMock())
        mock_client.run_until_complete.assert_called_once()


class TestResolveDestination:
    def test_save_to_watch_folder_returns_watch_folder_destination(self) -> None:
        with patch("app.destinations.get_settings") as m_get:
            m_get.return_value = Settings.model_construct(watch_folder="/tmp/watch")
            dest = resolve_destination(
                save_to_watch_folder=True,
                watch_folder_path="/tmp/watch",
            )
        assert isinstance(dest, WatchFolderDestination)

    def test_default_returns_client_destination(self) -> None:
        with patch("app.destinations.get_settings") as m_get:
            m_get.return_value = Settings.model_construct()
            dest = resolve_destination()
        assert isinstance(dest, ClientDestination)

    def test_download_background_returns_background_queue(self) -> None:
        with patch("app.destinations.get_settings") as m_get:
            m_get.return_value = Settings.model_construct(download_dir="/tmp/dl")
            dest = resolve_destination(
                download_direct=True,
                download_background=True,
                download_direct_path="/tmp/dl",
            )
        assert isinstance(dest, BackgroundQueueDestination)

    def test_download_direct_returns_direct_download(self) -> None:
        with patch("app.client.libtorrent_direct.LibtorrentDirectClient"):
            with patch("app.destinations.get_settings") as m_get:
                m_get.return_value = Settings.model_construct()
                dest = resolve_destination(
                    download_direct=True,
                    download_direct_path="/tmp/direct",
                )
            assert isinstance(dest, DirectDownloadDestination)

    def test_download_direct_without_torrentp_raises(self) -> None:
        with patch(
            "app.client.libtorrent_direct.LibtorrentDirectClient",
            MagicMock(side_effect=ImportError("No module named 'torrentp'")),
        ):
            with patch("app.destinations.get_settings") as m_get:
                m_get.return_value = Settings.model_construct()
                with pytest.raises(RuntimeError) as exc_info:
                    resolve_destination(
                        download_direct=True,
                        download_direct_path="/tmp/direct",
                    )
                assert "torrentp" in str(exc_info.value)
