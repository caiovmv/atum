"""Testes da CLI (Typer CliRunner)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from app.main import app

runner = CliRunner()


class TestVersion:
    def test_version_short(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output or "version" in result.output.lower()

    def test_version_long(self) -> None:
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0


class TestSearchCLI:
    def test_search_without_query_exits_with_message(self) -> None:
        result = runner.invoke(app, ["search"])
        assert result.exit_code != 0
        assert "termo de busca" in result.output.lower()

    def test_search_help_includes_organize(self) -> None:
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "organize" in result.output.lower()


class TestWishlistCLI:
    def test_wishlist_list_empty(self) -> None:
        result = runner.invoke(app, ["wishlist", "list"])
        assert result.exit_code == 0
        assert "vazia" in result.output or "ID" in result.output

    def test_wishlist_search_dry_run(self) -> None:
        result = runner.invoke(app, ["wishlist", "search", "--dry-run"])
        assert result.exit_code == 0


class TestResolveCLI:
    def test_resolve_album_without_key_exits(self) -> None:
        result = runner.invoke(app, ["resolve", "album", "The Wall"])
        assert result.exit_code != 0
        assert "LASTFM" in result.output or "api" in result.output.lower()


class TestFeedCLI:
    def test_feed_list_runs(self) -> None:
        result = runner.invoke(app, ["feed", "list"])
        assert result.exit_code == 0

    def test_feed_poll_no_auto_download(self) -> None:
        result = runner.invoke(app, ["feed", "poll"])
        assert result.exit_code == 0

    def test_feed_poll_accepts_include_exclude(self) -> None:
        # Mock feedparser para não acessar rede (evita IncompleteRead / falhas intermitentes)
        with patch("feedparser.parse") as m_parse:
            m_parse.return_value = type("Feed", (), {"bozo_exception": None, "entries": []})()
            result = runner.invoke(app, ["feed", "poll", "--include", "FLAC", "--exclude", "bootleg"])
        assert result.exit_code == 0

    def test_feed_pending_help(self) -> None:
        result = runner.invoke(app, ["feed", "pending", "--help"])
        assert result.exit_code == 0
        assert "pending" in result.output.lower()

    def test_feed_daemon_help(self) -> None:
        result = runner.invoke(app, ["feed", "daemon", "--help"])
        assert result.exit_code == 0
        assert "interval" in result.output.lower() or "--interval" in result.output


class TestBatchCLI:
    def test_batch_without_file_nor_stdin_exits_with_message(self) -> None:
        result = runner.invoke(app, ["batch"])
        assert result.exit_code != 0
        assert "arquivo" in result.output.lower() or "stdin" in result.output.lower()

    def test_batch_help(self) -> None:
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "stdin" in result.output or "arquivo" in result.output.lower()


class TestDownloadCLI:
    def test_download_list_runs(self) -> None:
        result = runner.invoke(app, ["download", "list"])
        assert result.exit_code == 0
        assert "Nenhum" in result.output or "download" in result.output.lower()

    def test_download_watch_help(self) -> None:
        result = runner.invoke(app, ["download", "watch", "--help"])
        assert result.exit_code == 0
        assert "intervalo" in result.output.lower() or "interval" in result.output.lower()
