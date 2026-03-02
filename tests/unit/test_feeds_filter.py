"""Testes dos filtros --include e --exclude em feeds."""

from __future__ import annotations

import pytest

from app.feeds import _matches_include_exclude


class TestMatchesIncludeExclude:
    def test_no_include_no_exclude_returns_true(self) -> None:
        assert _matches_include_exclude("Any Title", None, None) is True
        assert _matches_include_exclude("FLAC Album", [], None) is True

    def test_include_must_match(self) -> None:
        assert _matches_include_exclude("Artist - Album [FLAC]", ["FLAC"], None) is True
        assert _matches_include_exclude("Artist - Album [FLAC]", ["flac"], None) is True
        assert _matches_include_exclude("Artist - Album [FLAC]", ["320"], None) is False
        assert _matches_include_exclude("Some Title", ["FLAC", "320"], None) is False
        assert _matches_include_exclude("Some FLAC Title", ["FLAC", "320"], None) is True

    def test_exclude_must_not_match(self) -> None:
        assert _matches_include_exclude("Artist - Album", None, ["soundtrack"]) is True
        assert _matches_include_exclude("Artist - Soundtrack", None, ["soundtrack"]) is False
        assert _matches_include_exclude("Artist - Soundtrack", None, ["Soundtrack"]) is False
        assert _matches_include_exclude("Mix 2024", None, ["mix", "compilation"]) is False

    def test_include_and_exclude_combined(self) -> None:
        assert _matches_include_exclude("Artist - Album [FLAC]", ["FLAC"], ["bootleg"]) is True
        assert _matches_include_exclude("Artist - Album [FLAC] bootleg", ["FLAC"], ["bootleg"]) is False
        assert _matches_include_exclude("Artist - Album", ["FLAC"], None) is False
