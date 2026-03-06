"""Testes do módulo indexer_status (get_indexer_base_urls, run_health_cycle)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import Settings
from app.indexer_status import get_indexer_base_urls, run_health_cycle


class TestGetIndexerBaseUrls:
    def test_returns_only_configured_urls(self) -> None:
        s = Settings.model_construct(
            x1337_base_url="https://1337x.to",
            tpb_base_url="",
            yts_base_url="https://yts.lt",
        )
        urls = get_indexer_base_urls(s)
        assert "1337x" in urls
        assert urls["1337x"] == "https://1337x.to"
        assert "yts" in urls
        assert urls["yts"] == "https://yts.lt"
        assert "tpb" not in urls  # empty url omitted


class TestRunHealthCycle:
    @patch("app.search.probe_indexer")
    def test_returns_result_per_indexer(self, mock_probe: object) -> None:
        mock_probe.return_value = True
        s = Settings.model_construct(
            x1337_base_url="https://1337x.to",
            tpb_base_url="https://tpb.party",
            yts_base_url="",
            eztv_base_url="",
            nyaa_base_url="",
            limetorrents_base_url="",
            iptorrents_base_url="",
        )
        result = run_health_cycle(s, redis_url=None, probe_timeout_sec=5)
        assert result["1337x"] is True
        assert result["tpb"] is True
        assert mock_probe.call_count == 2

    @patch("app.search.probe_indexer")
    def test_marks_fail_when_probe_returns_false(self, mock_probe: object) -> None:
        def side_effect(name: str, **kwargs: object) -> bool:
            return name != "tpb"

        mock_probe.side_effect = side_effect
        s = Settings.model_construct(
            x1337_base_url="https://1337x.to",
            tpb_base_url="https://tpb.party",
            yts_base_url="",
            eztv_base_url="",
            nyaa_base_url="",
            limetorrents_base_url="",
            iptorrents_base_url="",
        )
        result = run_health_cycle(s, redis_url=None, probe_timeout_sec=5)
        assert result["1337x"] is True
        assert result["tpb"] is False
