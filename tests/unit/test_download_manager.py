"""Testes do gerenciador de downloads em background (download_manager)."""

from __future__ import annotations

import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.download_manager import add, delete, list_downloads, reconcile_downloads_with_filesystem, start, stop


class TestDownloadManagerAdd:
    """add(magnet, save_path, name) usa repositório (DIP) e cria o diretório."""

    def test_add_returns_id_and_creates_dir(self, tmp_path: Path) -> None:
        save_dir = tmp_path / "save"
        m_repo = MagicMock()
        m_repo.add.return_value = 1
        with patch("app.download_manager.get_repo", return_value=m_repo):
            out = add("magnet:?xt=urn:btih:abc", str(save_dir), "My Torrent")
            assert out == 1
            m_repo.add.assert_called_once()
            assert save_dir.exists()
            call_0 = m_repo.add.call_args[0]
            assert call_0[0] == "magnet:?xt=urn:btih:abc"
            assert "save" in call_0[1]
            assert call_0[2] == "My Torrent"

    def test_add_resolves_path(self, tmp_path: Path) -> None:
        m_repo = MagicMock()
        m_repo.add.return_value = 42
        with patch("app.download_manager.get_repo", return_value=m_repo):
            add("magnet:?xt=urn:btih:x", str(tmp_path), None)
            call_path = m_repo.add.call_args[0][1]
            assert Path(call_path).is_absolute()


class TestDownloadManagerList:
    def test_list_downloads_calls_repo(self) -> None:
        m_repo = MagicMock()
        m_repo.list.return_value = [{"id": 1, "status": "queued"}]
        with patch("app.download_manager.get_repo", return_value=m_repo):
            out = list_downloads()
            assert out == [{"id": 1, "status": "queued"}]
            m_repo.list.assert_called_once_with(status_filter=None)

    def test_list_downloads_with_filter(self) -> None:
        m_repo = MagicMock()
        m_repo.list.return_value = []
        with patch("app.download_manager.get_repo", return_value=m_repo):
            list_downloads(status_filter="completed")
            m_repo.list.assert_called_once_with(status_filter="completed")


class TestReconcileDownloadsWithFilesystem:
    """reconcile_downloads_with_filesystem() remove do repositório completed cujo content_path não existe."""

    def test_removes_completed_when_path_missing(self) -> None:
        m_repo = MagicMock()
        m_repo.list.return_value = [
            {"id": 1, "content_path": "/some/path", "status": "completed"},
        ]
        m_repo.delete.return_value = True
        with patch("app.download_manager.Path") as m_path_cls, patch(
            "app.download_manager.get_repo", return_value=m_repo
        ):
            m_path_cls.return_value.exists.return_value = False
            n = reconcile_downloads_with_filesystem()
            assert n == 1
            m_repo.delete.assert_called_once_with(1)

    def test_keeps_completed_when_path_exists(self) -> None:
        m_repo = MagicMock()
        m_repo.list.return_value = [
            {"id": 1, "content_path": "/existing/path", "status": "completed"},
        ]
        with patch("app.download_manager.Path") as m_path_cls, patch(
            "app.download_manager.get_repo", return_value=m_repo
        ):
            m_path_cls.return_value.exists.return_value = True
            n = reconcile_downloads_with_filesystem()
            assert n == 0
            m_repo.delete.assert_not_called()

    def test_skips_completed_without_content_path(self) -> None:
        m_repo = MagicMock()
        m_repo.list.return_value = [
            {"id": 1, "content_path": None, "status": "completed"},
            {"id": 2, "content_path": "", "status": "completed"},
        ]
        with patch("app.download_manager.get_repo", return_value=m_repo):
            n = reconcile_downloads_with_filesystem()
            assert n == 0
            m_repo.delete.assert_not_called()


class TestDownloadManagerStart:
    def test_start_no_row_returns_false(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = None
        with patch("app.download_manager.get_repo", return_value=m_repo):
            assert start(999) is False
            m_repo.get.assert_called_once_with(999)

    def test_start_wrong_status_returns_false(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {"id": 1, "status": "completed"}
        with patch("app.download_manager.get_repo", return_value=m_repo):
            assert start(1) is False

    def test_start_queued_starts_thread(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {"id": 1, "status": "queued"}
        with patch("app.download_manager.get_repo", return_value=m_repo), patch(
            "app.download_manager.threading.Thread"
        ) as m_thread_cls:
            m_thread = MagicMock()
            m_thread_cls.return_value = m_thread
            assert start(1) is True
            m_thread_cls.assert_called_once()
            assert m_thread_cls.call_args[1]["daemon"] is True
            assert "download-1" in m_thread_cls.call_args[1]["name"]
            m_thread.start.assert_called_once()

    def test_start_paused_starts_thread(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {"id": 1, "status": "paused"}
        with patch("app.download_manager.get_repo", return_value=m_repo), patch(
            "app.download_manager.threading.Thread"
        ) as m_thread_cls:
            m_thread_cls.return_value = MagicMock()
            assert start(1) is True

    def test_start_thread_start_fails_returns_false(self) -> None:
        import app.download_manager as dm
        dm._worker_threads.pop(1, None)
        dm._worker_stop_events.pop(1, None)
        m_repo = MagicMock()
        m_repo.get.return_value = {"id": 1, "status": "queued"}
        with patch("app.download_manager.get_repo", return_value=m_repo), patch(
            "app.download_manager.threading.Thread"
        ) as m_thread_cls:
            m_thread = MagicMock()
            m_thread.start.side_effect = OSError("Cannot start thread")
            m_thread_cls.return_value = m_thread
            assert start(1) is False


class TestDownloadManagerStop:
    def test_stop_no_row_returns_false(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = None
        with patch("app.download_manager.get_repo", return_value=m_repo):
            assert stop(999) is False

    def test_stop_no_pid_returns_true_if_acceptable_status(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {"id": 1, "status": "queued", "pid": None}
        with patch("app.download_manager.get_repo", return_value=m_repo):
            assert stop(1) is True

    def test_stop_with_pid_kills_and_updates_repo(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {"id": 1, "status": "downloading", "pid": 12345}
        with patch("app.download_manager.get_repo", return_value=m_repo), patch(
            "app.download_manager.os.kill"
        ) as m_kill:
            assert stop(1) is True
            m_kill.assert_called_once_with(12345, signal.SIGTERM)
            m_repo.update_status.assert_called_once()
            m_repo.set_pid.assert_called_once_with(1, None)

    def test_stop_kill_raises_process_lookup_ignored(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {"id": 1, "status": "downloading", "pid": 99999}
        with patch("app.download_manager.get_repo", return_value=m_repo), patch(
            "app.download_manager.os.kill",
            side_effect=ProcessLookupError(),
        ):
            assert stop(1) is True


class TestDownloadManagerDelete:
    def test_delete_no_row_returns_false(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = None
        with patch("app.download_manager.get_repo", return_value=m_repo):
            assert delete(999) is False

    def test_delete_calls_repo_delete(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {"id": 1, "pid": None}
        m_repo.delete.return_value = True
        with patch("app.download_manager.get_repo", return_value=m_repo):
            assert delete(1) is True
            m_repo.delete.assert_called_once_with(1)

    def test_delete_with_pid_kills_first(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {"id": 1, "pid": 12345}
        m_repo.delete.return_value = True
        with patch("app.download_manager.get_repo", return_value=m_repo), patch(
            "app.download_manager.os.kill"
        ):
            assert delete(1) is True
            m_repo.delete.assert_called_once_with(1)
