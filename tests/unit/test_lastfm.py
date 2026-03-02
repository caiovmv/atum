"""Testes do módulo Last.fm (lastfm.py) com requests mockado."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.lastfm import get_chart_tracks, resolve_album, resolve_artist_album


class TestResolveAlbum:
    """Testes de resolve_album."""

    def test_empty_api_key_returns_empty(self) -> None:
        assert resolve_album("The Wall", "") == []
        assert resolve_album("The Wall", "   ") == []

    def test_empty_album_returns_empty(self) -> None:
        assert resolve_album("", "key") == []
        assert resolve_album("   ", "key") == []

    @patch("app.lastfm.requests.get")
    def test_parses_json_response(self, mock_get: object) -> None:
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "results": {
                "albummatches": {
                    "album": [
                        {"artist": "Pink Floyd", "name": "The Wall"},
                        {"artist": "Weezer", "name": "Make Believe"},
                    ]
                }
            }
        }
        result = resolve_album("The Wall", "api_key", limit=10)
        assert len(result) == 2
        assert result[0] == {"artist": "Pink Floyd", "name": "The Wall"}
        assert result[1] == {"artist": "Weezer", "name": "Make Believe"}

    @patch("app.lastfm.requests.get")
    def test_respects_limit(self, mock_get: object) -> None:
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "results": {
                "albummatches": {
                    "album": [
                        {"artist": f"A{i}", "name": f"B{i}"} for i in range(15)
                    ]
                }
            }
        }
        result = resolve_album("x", "key", limit=3)
        assert len(result) == 3

    @patch("app.lastfm.requests.get")
    def test_api_error_returns_empty(self, mock_get: object) -> None:
        mock_get.side_effect = Exception("Network error")
        assert resolve_album("The Wall", "key") == []


class TestResolveArtistAlbum:
    """Testes de resolve_artist_album."""

    def test_both_empty_returns_none(self) -> None:
        assert resolve_artist_album("", "", "key") is None

    def test_only_album_no_key_returns_album(self) -> None:
        assert resolve_artist_album("", "The Wall", "") == "The Wall"

    @patch("app.lastfm.resolve_album")
    def test_only_album_with_key_uses_resolve_album(self, mock_resolve: object) -> None:
        mock_resolve.return_value = [{"artist": "Pink Floyd", "name": "The Wall"}]
        assert resolve_artist_album("", "The Wall", "key") == "Pink Floyd - The Wall"
        mock_resolve.assert_called_once_with("The Wall", "key", limit=1)

    def test_only_artist_returns_artist(self) -> None:
        assert resolve_artist_album("Pink Floyd", "", "key") == "Pink Floyd"

    @patch("app.lastfm.requests.get")
    def test_both_success_returns_artist_album(self, mock_get: object) -> None:
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "album": {
                "name": "The Wall",
                "artist": {"name": "Pink Floyd"},
            }
        }
        assert resolve_artist_album("Pink Floyd", "The Wall", "key") == "Pink Floyd - The Wall"

    @patch("app.lastfm.requests.get")
    def test_both_api_fail_returns_concatenated(self, mock_get: object) -> None:
        mock_get.side_effect = Exception("API error")
        assert resolve_artist_album("Pink Floyd", "The Wall", "key") == "Pink Floyd - The Wall"


class TestGetChartTracks:
    """Testes de get_chart_tracks (chart.getTopTracks)."""

    def test_empty_api_key_returns_empty(self) -> None:
        assert get_chart_tracks("") == []
        assert get_chart_tracks("   ") == []

    @patch("app.lastfm.requests.get")
    def test_parses_json_response(self, mock_get: object) -> None:
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "tracks": {
                "track": [
                    {"artist": {"name": "Artist A"}, "name": "Track One"},
                    {"artist": {"name": "Artist B"}, "name": "Track Two"},
                ]
            }
        }
        result = get_chart_tracks("api_key", limit=10)
        assert len(result) == 2
        assert result[0] == {"artist": "Artist A", "name": "Track One"}
        assert result[1] == {"artist": "Artist B", "name": "Track Two"}

    @patch("app.lastfm.requests.get")
    def test_respects_limit_and_page(self, mock_get: object) -> None:
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.json.return_value = {
            "tracks": {
                "track": [
                    {"artist": {"name": f"A{i}"}, "name": f"T{i}"} for i in range(5)
                ]
            }
        }
        result = get_chart_tracks("key", limit=5, page=1)
        assert len(result) == 5
        mock_get.assert_called_once()
        call_kw = mock_get.call_args[1]
        assert call_kw["params"].get("limit") == 5
        assert call_kw["params"].get("page") == 1

    @patch("app.lastfm.requests.get")
    def test_api_error_returns_empty(self, mock_get: object) -> None:
        mock_get.side_effect = Exception("Network error")
        assert get_chart_tracks("key") == []
