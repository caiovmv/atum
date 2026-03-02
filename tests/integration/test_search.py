"""Testes do módulo de busca (search.py) com indexadores mockados."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.quality import parse_quality
from app.search import (
    SearchResult,
    get_magnet_for_result,
    search_all,
    search_tg,
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

    def test_tg_returns_magnet(self) -> None:
        r = SearchResult(
            title="Album",
            quality=parse_quality("FLAC"),
            seeders=0,
            size="",
            torrent_id="x",
            indexer="tg",
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


class TestSearchTg:
    """Testes de search_tg com requests mockado."""

    @patch("requests.get")
    def test_parses_html_and_returns_results(self, mock_get: object) -> None:
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.text = '''
        <div><a href="other">x</a></div>
        <a title="Pink Floyd - The Wall FLAC 2024" href="magnet:?xt=urn:btih:abc123">DL</a>
        '''
        results = search_tg("Pink Floyd", limit=5, no_quality_filter=True)
        assert len(results) >= 1
        assert any("Pink Floyd" in r.title or "The Wall" in r.title for r in results)
        assert results[0].indexer == "tg"
        assert results[0].magnet == "magnet:?xt=urn:btih:abc123"

    @patch("requests.get")
    def test_request_error_returns_empty(self, mock_get: object) -> None:
        mock_get.side_effect = Exception("Timeout")
        results = search_tg("test", verbose=False)
        assert results == []
