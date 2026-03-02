"""Testes da renderização da lista de downloads (presentation/download_list_view)."""

from __future__ import annotations

import builtins
from unittest.mock import MagicMock, patch

from app.presentation.download_list_view import render_downloads_table


class TestRenderDownloadsTable:
    def test_empty_list_does_not_crash(self) -> None:
        render_downloads_table([])

    def test_with_rich_prints_table(self) -> None:
        with patch("rich.console.Console") as m_console_cls, patch(
            "rich.table.Table"
        ) as m_table_cls:
            mock_console = MagicMock()
            m_console_cls.return_value = mock_console
            mock_table = MagicMock()
            m_table_cls.return_value = mock_table
            render_downloads_table(
                [
                    {
                        "id": 1,
                        "status": "queued",
                        "progress": 0,
                        "name": "Album FLAC",
                        "save_path": "/tmp",
                    }
                ]
            )
            mock_table.add_row.assert_called()
            mock_console.print.assert_called_once_with(mock_table)

    def test_fallback_without_rich_echos_lines(self) -> None:
        """Quando rich não está disponível, usa typer.echo para cada linha."""
        real_import = builtins.__import__

        def fake_import(name: str, *args: object, **kwargs: object):
            if name == "rich.console" or name == "rich.table" or name == "rich":
                raise ImportError("No module named 'rich'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with patch("app.presentation.download_list_view.typer.echo") as m_echo:
                render_downloads_table(
                    [
                        {
                            "id": 1,
                            "status": "downloading",
                            "progress": 50.0,
                            "name": "Artist - Album",
                            "magnet": "magnet:?xt=urn:btih:abc",
                        }
                    ]
                )
                m_echo.assert_called()
                call_args = m_echo.call_args[0][0]
                assert "1" in call_args
                assert "downloading" in call_args
                assert "50" in call_args
                assert "Artist" in call_args or "Album" in call_args

    def test_row_with_missing_fields_uses_defaults(self) -> None:
        with patch("rich.console.Console") as m_console_cls, patch(
            "rich.table.Table"
        ) as m_table_cls:
            mock_console = MagicMock()
            m_console_cls.return_value = mock_console
            mock_table = MagicMock()
            m_table_cls.return_value = mock_table
            render_downloads_table([{"id": 2}])
            mock_table.add_row.assert_called_once()
            row_args = mock_table.add_row.call_args[0]
            assert row_args[0] == "2"
            assert "?" in str(row_args[1]) or row_args[1] == "?"
