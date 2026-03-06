"""Testes do worker de download em subprocesso (download_worker)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.download_worker import run_worker


class TestRunWorker:
    def test_no_row_returns_early(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = None
        with patch("app.repositories.download_repository.get_repo", return_value=m_repo):
            run_worker(999)
            m_repo.get.assert_called_once_with(999)
            m_repo.update_status.assert_not_called()

    def test_wrong_status_returns_early(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {
            "id": 1,
            "magnet": "magnet:?xt=urn:btih:abc",
            "save_path": "/tmp",
            "status": "completed",
        }
        with patch("app.repositories.download_repository.get_repo", return_value=m_repo):
            run_worker(1)
            m_repo.update_status.assert_not_called()
            m_repo.set_pid.assert_not_called()

    def test_queued_updates_status_and_pid_then_completes(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {
            "id": 1,
            "magnet": "magnet:?xt=urn:btih:abc",
            "save_path": "/tmp",
            "status": "queued",
        }
        # Worker usa libtorrent_engine primeiro; mock run_download para retornar sucesso
        with patch("app.repositories.download_repository.get_repo", return_value=m_repo), patch(
            "app.download_worker.os.getpid", return_value=12345
        ), patch(
            "app.client.libtorrent_engine.run_download",
            return_value=(True, "MyAlbum"),
        ):
            run_worker(1)
            m_repo.update_status.assert_any_call(1, "downloading")
            m_repo.set_pid.assert_any_call(1, 12345)
            m_repo.update_status.assert_any_call(1, "completed", progress=100.0)
            m_repo.set_pid.assert_any_call(1, None)
            m_repo.set_content_path.assert_called_once()
            call_args = m_repo.set_content_path.call_args[0]
            assert call_args[0] == 1
            assert "MyAlbum" in call_args[1]
            assert "tmp" in call_args[1] or "tmp" in str(call_args[1])

    def test_exception_updates_status_failed(self) -> None:
        m_repo = MagicMock()
        m_repo.get.return_value = {
            "id": 1,
            "magnet": "magnet:?xt=urn:btih:abc",
            "save_path": "/tmp",
            "status": "queued",
        }
        # Forçar exceção ao chamar run_download (caminho libtorrent)
        with patch("app.repositories.download_repository.get_repo", return_value=m_repo), patch(
            "app.download_worker.os.getpid", return_value=11111
        ), patch(
            "app.client.libtorrent_engine.run_download",
            side_effect=RuntimeError("Connection lost"),
        ):
            run_worker(1)
            m_repo.update_status.assert_any_call(
                1, "failed", error_message="RuntimeError: Connection lost"
            )
            m_repo.set_pid.assert_any_call(1, None)
