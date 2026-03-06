"""Testes do módulo de busca (search.py) com indexadores mockados."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.quality import parse_quality
from app.search import (
    SearchResult,
    get_magnet_for_result,
    probe_indexer,
    search_all,
)


class TestGetMagnetForResult:
    """Testes de get_magnet_for_result."""

    def test_returns_magnet_when_present(self) -> None:
        r = SearchResult(
            title="Album FLAC",
            quality=parse_quality("FLAC"),
            seeders=10,
            size="300 MB",
            torrent_id="x",
            indexer="tpb",
            magnet="magnet:?xt=urn:btih:abc",
        )
        assert get_magnet_for_result(r) == "magnet:?xt=urn:btih:abc"

    def test_tpb_returns_magnet(self) -> None:
        r = SearchResult(
            title="Album",
            quality=parse_quality("FLAC"),
            seeders=0,
            size="",
            torrent_id="x",
            indexer="tpb",
            magnet="magnet:?xt=urn:btih:xyz",
        )
        assert get_magnet_for_result(r) == "magnet:?xt=urn:btih:xyz"

    @patch("app.search.get_magnet_1337x")
    def test_1337x_calls_get_magnet_1337x(self, mock_get: object) -> None:
        mock_get.return_value = "magnet:?xt=urn:btih:1337"
        r = SearchResult(
            title="Album",
            quality=parse_quality("FLAC"),
            seeders=5,
            size="100 MB",
            torrent_id="tid123",
            indexer="1337x",
            magnet=None,
        )
        assert get_magnet_for_result(r) == "magnet:?xt=urn:btih:1337"
        mock_get.assert_called_once_with("tid123")

    @patch("app.search.get_magnet_1337x")
    def test_1337x_returns_none_when_get_fails(self, mock_get: object) -> None:
        mock_get.return_value = None
        r = SearchResult(
            title="X",
            quality=parse_quality("FLAC"),
            seeders=0,
            size="",
            torrent_id="tid",
            indexer="1337x",
            magnet=None,
        )
        assert get_magnet_for_result(r) is None


class TestSearchAll:
    """Testes de search_all com indexadores mockados."""

    @patch("app.search.search_tpb")
    @patch("app.search.search_1337x")
    def test_merges_and_sorts_results(
        self,
        mock_1337x: object,
        mock_tpb: object,
    ) -> None:
        from app.quality import parse_quality
        q_flac = parse_quality("FLAC")
        q_320 = parse_quality("320")
        mock_1337x.return_value = [
            SearchResult("1337x FLAC", q_flac, 5, "200 MB", "t1", "1337x", None),
        ]
        mock_tpb.return_value = [
            SearchResult("TPB 320", q_320, 10, "150 MB", "t2", "tpb", "magnet:t2"),
        ]
        results = search_all("test", limit=10, indexers=["1337x", "tpb"])
        assert len(results) == 2
        # Ordenação padrão: seeders (maior primeiro), depois leechers, depois qualidade
        assert results[0].title == "TPB 320"  # 10 seeders
        assert results[1].title == "1337x FLAC"  # 5 seeders
        mock_1337x.assert_called_once()
        mock_tpb.assert_called_once()

    @patch("app.search.search_tpb")
    @patch("app.search.search_1337x")
    def test_only_calls_requested_indexers(
        self,
        mock_1337x: object,
        mock_tpb: object,
    ) -> None:
        mock_1337x.return_value = []
        mock_tpb.return_value = []
        search_all("q", limit=5, indexers=["1337x"])
        mock_1337x.assert_called_once()
        mock_tpb.assert_not_called()


class TestProbeIndexer:
    """Testes de probe_indexer (health-check por busca)."""

    def test_iptorrents_returns_true_stub(self) -> None:
        assert probe_indexer("iptorrents") is True

    def test_unknown_indexer_returns_false(self) -> None:
        assert probe_indexer("unknown") is False
        assert probe_indexer("tg") is False

    @patch("app.search.search_1337x")
    def test_1337x_success_returns_true(self, mock_1337x: object) -> None:
        mock_1337x.return_value = []
        assert probe_indexer("1337x", timeout_sec=5) is True
        mock_1337x.assert_called_once()

    @patch("app.search.search_1337x")
    def test_1337x_exception_returns_false(self, mock_1337x: object) -> None:
        mock_1337x.side_effect = Exception("timeout")
        assert probe_indexer("1337x", timeout_sec=5) is False
