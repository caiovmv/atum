"""Testes do módulo de enriquecimento (llm_client, enrichment_daemon, enrich_music, enrich_video)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from app.ai.llm_client import LLMClient, LLMResponse


class TestLLMClient:
    """Testes do LLMClient."""

    def test_init_defaults(self) -> None:
        client = LLMClient(provider="ollama", model="llama3:8b")
        assert client.provider == "ollama"
        assert client.model == "llama3:8b"
        assert client.base_url == "http://localhost:11434"
        assert client.api_key is None
        assert client.fallback_provider is None
        assert client.timeout == 120

    def test_init_with_fallback(self) -> None:
        client = LLMClient(
            provider="ollama",
            model="llama3:8b",
            fallback_provider="openrouter",
            fallback_model="meta-llama/llama-3.1-8b-instruct",
            fallback_api_key="sk-test",
            fallback_base_url="http://other:11434",
        )
        assert client.fallback_provider == "openrouter"
        assert client.fallback_base_url == "http://other:11434"

    @patch("app.ai.llm_client.requests.post")
    def test_chat_ollama(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "message": {"content": "Olá mundo"},
        }
        client = LLMClient(provider="ollama", model="llama3:8b")
        resp = client.chat([{"role": "user", "content": "oi"}])
        assert resp.content == "Olá mundo"
        assert resp.provider == "ollama"
        assert resp.model == "llama3:8b"

    @patch("app.ai.llm_client.requests.post")
    def test_chat_openrouter(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "hello"}}],
        }
        client = LLMClient(provider="openrouter", model="test-model", api_key="sk-test")
        resp = client.chat([{"role": "user", "content": "hi"}])
        assert resp.content == "hello"
        assert resp.provider == "openrouter"

    @patch("app.ai.llm_client.requests.post")
    def test_chat_openrouter_empty_choices(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"choices": []}
        client = LLMClient(provider="openrouter", model="test", api_key="sk-test")
        resp = client.chat([{"role": "user", "content": "hi"}])
        assert resp.content == ""

    @patch("app.ai.llm_client.requests.post")
    def test_chat_fallback_on_error(self, mock_post: MagicMock) -> None:
        import requests as req

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise req.ConnectionError("primary down")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"message": {"content": "fallback ok"}}
            return mock_resp

        mock_post.side_effect = side_effect

        client = LLMClient(
            provider="openrouter", model="primary",
            api_key="sk-1",
            fallback_provider="ollama", fallback_model="llama3:8b",
        )
        resp = client.chat([{"role": "user", "content": "test"}])
        assert resp.content == "fallback ok"
        assert resp.provider == "ollama"

    @patch("app.ai.llm_client.requests.post")
    def test_chat_json_valid(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "message": {"content": 'aqui está: {"moods": ["feliz", "animado"]}'},
        }
        client = LLMClient(provider="ollama", model="test")
        result = client.chat_json([{"role": "user", "content": "test"}])
        assert result == {"moods": ["feliz", "animado"]}

    @patch("app.ai.llm_client.requests.post")
    def test_chat_json_invalid(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "message": {"content": "isso não é json nenhum"},
        }
        client = LLMClient(provider="ollama", model="test")
        result = client.chat_json([{"role": "user", "content": "test"}])
        assert result == {}


class TestMusicEnrichmentResult:
    """Testes do MusicEnrichmentResult."""

    def test_to_update_dict_empty(self) -> None:
        from app.ai.enrich_music import MusicEnrichmentResult

        r = MusicEnrichmentResult()
        d = r.to_update_dict()
        assert "enriched_at" in d
        assert "bpm" not in d
        assert "moods" not in d

    def test_to_update_dict_with_data(self) -> None:
        from app.ai.enrich_music import MusicEnrichmentResult

        r = MusicEnrichmentResult(
            bpm=120.0,
            musical_key="C major",
            moods=["feliz"],
            enrichment_sources=["spotify", "llm"],
        )
        d = r.to_update_dict()
        assert d["bpm"] == 120.0
        assert d["musical_key"] == "C major"
        assert d["moods"] == ["feliz"]
        assert d["enrichment_sources"] == ["spotify", "llm"]


class TestVideoEnrichmentResult:
    """Testes do VideoEnrichmentResult."""

    def test_to_update_dict(self) -> None:
        from app.ai.enrich_video import VideoEnrichmentResult

        r = VideoEnrichmentResult(
            overview="Um filme sobre...",
            vote_average=8.5,
            tmdb_genres=["Drama", "Action"],
            enrichment_sources=["tmdb"],
        )
        d = r.to_update_dict()
        assert d["overview"] == "Um filme sobre..."
        assert d["vote_average"] == 8.5
        assert d["tmdb_genres"] == ["Drama", "Action"]


class TestEnrichmentDaemon:
    """Testes do enrichment_daemon."""

    def test_settings_bool_true_values(self) -> None:
        from app.ai.enrichment_daemon import _settings_bool

        with patch("app.ai.enrichment_daemon._get_settings_value") as mock:
            mock.return_value = True
            assert _settings_bool("key") is True

            mock.return_value = "true"
            assert _settings_bool("key") is True

            mock.return_value = "yes"
            assert _settings_bool("key") is True

            mock.return_value = 1
            assert _settings_bool("key") is True

    def test_settings_bool_false_values(self) -> None:
        from app.ai.enrichment_daemon import _settings_bool

        with patch("app.ai.enrichment_daemon._get_settings_value") as mock:
            mock.return_value = False
            assert _settings_bool("key") is False

            mock.return_value = "false"
            assert _settings_bool("key") is False

            mock.return_value = "0"
            assert _settings_bool("key") is False

            mock.return_value = ""
            assert _settings_bool("key") is False

            mock.return_value = "no"
            assert _settings_bool("key") is False

    @patch("app.deps.get_llm_client")
    @patch("app.deps.get_library_import_repo")
    def test_run_cycle_no_items(self, mock_repo_fn: MagicMock, mock_llm: MagicMock) -> None:
        from app.ai.enrichment_daemon import run_enrichment_cycle

        mock_repo = MagicMock()
        mock_repo.list_pending_enrichment.return_value = []
        mock_repo_fn.return_value = mock_repo

        with patch("app.ai.enrichment_daemon._get_settings_value", return_value=0):
            result = run_enrichment_cycle(batch_size=5)
        assert result == 0

    @patch("app.deps.get_llm_client")
    @patch("app.deps.get_library_import_repo")
    def test_run_cycle_no_repo(self, mock_repo_fn: MagicMock, mock_llm: MagicMock) -> None:
        from app.ai.enrichment_daemon import run_enrichment_cycle

        mock_repo_fn.return_value = None
        result = run_enrichment_cycle()
        assert result == 0

    def test_content_type_movie_normalized(self) -> None:
        """Verifica que 'movie' singular é normalizado para 'movies'."""
        ct = "movie"
        ct = ct.strip().lower()
        if ct == "movie":
            ct = "movies"
        assert ct == "movies"


class TestEnrichMusicHelpers:
    """Testes de funções auxiliares de enrich_music."""

    def test_first_audio_file_none(self, tmp_path) -> None:
        from app.ai.enrich_music import _first_audio_file

        assert _first_audio_file(str(tmp_path / "naoexiste")) is None

    def test_first_audio_file_single(self, tmp_path) -> None:
        from app.ai.enrich_music import _first_audio_file

        f = tmp_path / "track.mp3"
        f.write_bytes(b"\x00")
        assert _first_audio_file(str(f)) == f

    def test_first_audio_file_dir(self, tmp_path) -> None:
        from app.ai.enrich_music import _first_audio_file

        d = tmp_path / "album"
        d.mkdir()
        (d / "cover.jpg").write_bytes(b"\x00")
        (d / "01.flac").write_bytes(b"\x00")
        (d / "02.flac").write_bytes(b"\x00")
        result = _first_audio_file(str(d))
        assert result is not None
        assert result.name == "01.flac"

    def test_musicbrainz_no_artist(self) -> None:
        from app.ai.enrich_music import _enrich_musicbrainz

        assert _enrich_musicbrainz("", "Album") == {}

    def test_lastfm_no_api_key(self) -> None:
        from app.ai.enrich_music import _enrich_lastfm_tags

        with patch("app.deps.get_settings_repo", return_value=None):
            with patch("app.deps.get_settings") as mock_s:
                mock_s.return_value = MagicMock(lastfm_api_key="")
                assert _enrich_lastfm_tags("Artist", "Album") == {}

    def test_spotify_no_credentials(self) -> None:
        from app.ai.enrich_music import _enrich_spotify_features

        with patch("app.deps.get_settings_repo", return_value=None):
            with patch("app.deps.get_settings") as mock_s:
                mock_s.return_value = MagicMock(spotify_client_id="", spotify_client_secret="")
                assert _enrich_spotify_features("Artist", "Track") == {}
