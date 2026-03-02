"""Testes do módulo Spotify (spotify.py) com requests e arquivo mockados."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.spotify import (
    exchange_code_for_tokens,
    get_authorize_url,
    get_playlist_tracks,
    get_current_user_playlists,
    refresh_access_token,
    load_tokens,
    save_tokens,
    ensure_valid_token,
)


class TestGetAuthorizeUrl:
    def test_returns_url_with_params(self) -> None:
        url = get_authorize_url("client_id", "http://localhost:8765/callback", state="xyz")
        assert "accounts.spotify.com/authorize" in url
        assert "client_id=client_id" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        assert "state=xyz" in url
        assert "response_type=code" in url


class TestExchangeCodeForTokens:
    @patch("app.spotify.requests.post")
    def test_returns_tokens(self, mock_post: object) -> None:
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 3600,
        }
        result = exchange_code_for_tokens(
            "code", "cid", "secret", "http://localhost:8765/callback"
        )
        assert result["access_token"] == "at"
        assert result["refresh_token"] == "rt"
        assert result["expires_in"] == 3600


class TestRefreshAccessToken:
    @patch("app.spotify.requests.post")
    def test_returns_new_access_token(self, mock_post: object) -> None:
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {
            "access_token": "new_at",
            "expires_in": 3600,
        }
        result = refresh_access_token("rt", "cid", "secret")
        assert result["access_token"] == "new_at"
        assert result["expires_in"] == 3600


class TestLoadSaveTokens:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        with patch("app.spotify._tokens_path", return_value=tmp_path / "tokens.json"):
            save_tokens("at1", "rt1", 3600)
            data = load_tokens()
        assert data is not None
        assert data["access_token"] == "at1"
        assert data["refresh_token"] == "rt1"
        assert "expires_at" in data

    def test_load_missing_returns_none(self) -> None:
        with patch("app.spotify._tokens_path", return_value=Path("/nonexistent/tokens.json")):
            assert load_tokens() is None


class TestEnsureValidToken:
    @patch("app.spotify.load_tokens")
    def test_no_tokens_raises(self, mock_load: object) -> None:
        mock_load.return_value = None
        with pytest.raises(RuntimeError, match="não autenticado"):
            ensure_valid_token("cid", "secret")

    @patch("app.spotify.load_tokens")
    def test_valid_token_returns_it(self, mock_load: object) -> None:
        mock_load.return_value = {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_at": time.time() + 3600,
        }
        assert ensure_valid_token("cid", "secret") == "at"

    @patch("app.spotify.refresh_access_token")
    @patch("app.spotify.save_tokens")
    @patch("app.spotify.load_tokens")
    def test_expired_refreshes_and_returns(
        self, mock_load: object, mock_save: object, mock_refresh: object
    ) -> None:
        mock_load.return_value = {
            "access_token": "old_at",
            "refresh_token": "rt",
            "expires_at": time.time() - 10,
        }
        mock_refresh.return_value = {
            "access_token": "new_at",
            "expires_in": 3600,
            "refresh_token": "rt",
        }
        result = ensure_valid_token("cid", "secret")
        assert result == "new_at"
        mock_refresh.assert_called_once_with("rt", "cid", "secret")
        mock_save.assert_called_once()


class TestGetCurrentUserPlaylists:
    @patch("app.spotify._api_get")
    def test_returns_playlists(self, mock_get: object) -> None:
        mock_get.return_value = {
            "items": [
                {"id": "p1", "name": "Playlist 1"},
                {"id": "p2", "name": "Playlist 2"},
            ],
        }
        result = get_current_user_playlists("token", limit=50)
        assert len(result) == 2
        assert result[0]["id"] == "p1"
        assert result[0]["name"] == "Playlist 1"


class TestGetPlaylistTracks:
    @patch("app.spotify._api_get")
    def test_returns_artist_track_lines(self, mock_get: object) -> None:
        mock_get.return_value = {
            "items": [
                {
                    "track": {
                        "name": "Song One",
                        "artists": [{"name": "Artist A"}],
                    },
                },
                {
                    "track": {
                        "name": "Song Two",
                        "artists": [{"name": "Artist B1"}, {"name": "Artist B2"}],
                    },
                },
            ],
        }
        result = get_playlist_tracks("playlist_id", "token")
        assert len(result) == 2
        assert result[0] == {"artist": "Artist A", "name": "Song One"}
        assert result[1] == {"artist": "Artist B1, Artist B2", "name": "Song Two"}

    @patch("app.spotify._api_get")
    def test_skips_null_track(self, mock_get: object) -> None:
        mock_get.return_value = {
            "items": [
                {"track": None},
                {"track": {"name": "Only", "artists": [{"name": "X"}]}},
            ],
        }
        result = get_playlist_tracks("pid", "token")
        assert len(result) == 1
        assert result[0] == {"artist": "X", "name": "Only"}
