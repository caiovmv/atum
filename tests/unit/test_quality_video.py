"""Testes do parser de qualidade de vídeo (quality_video.py)."""

from __future__ import annotations

import pytest

from app.quality_video import (
    VideoQualityInfo,
    VideoQualityScore,
    is_acceptable_video,
    matches_format_video,
    parse_format_filter_video,
    parse_quality_video,
)


class TestParseQualityVideo:
    def test_empty_returns_unknown(self) -> None:
        info = parse_quality_video("")
        assert info.kind == "unknown"
        assert info.score == VideoQualityScore.UNKNOWN
        assert info.resolution_p is None

    def test_720p_detected(self) -> None:
        info = parse_quality_video("Show Name S01E05 720p x264")
        assert info.kind == "720p"
        assert info.resolution_p == 720
        assert info.score >= VideoQualityScore.P720  # pode ter bônus de codec

    def test_1080p_detected(self) -> None:
        info = parse_quality_video("Movie Name (2020) 1080p BluRay x265")
        assert info.kind == "1080p"
        assert info.resolution_p == 1080
        assert info.score >= VideoQualityScore.P1080

    def test_2160p_4k_detected(self) -> None:
        info = parse_quality_video("Movie 2160p 4K UHD")
        assert info.kind == "2160p"
        assert info.resolution_p == 2160
        assert info.score == VideoQualityScore.P2160

    def test_x265_bonus(self) -> None:
        a = parse_quality_video("Title 1080p x264")
        b = parse_quality_video("Title 1080p x265")
        assert b.score >= a.score

    def test_source_bluray_webdl(self) -> None:
        info = parse_quality_video("Title 1080p BluRay x264")
        assert info.source == "bluray"
        info2 = parse_quality_video("Title 1080p WEB-DL")
        assert info2.source == "webdl"

    def test_label(self) -> None:
        info = parse_quality_video("X 1080p x265 BluRay")
        assert "1080p" in info.label
        assert "X265" in info.label or "x265" in info.label


class TestParseFormatFilterVideo:
    def test_none_or_empty_returns_none(self) -> None:
        assert parse_format_filter_video(None) is None
        assert parse_format_filter_video("") is None
        assert parse_format_filter_video("   ") is None

    def test_single_kind(self) -> None:
        assert parse_format_filter_video("1080p") == {"1080p"}
        assert parse_format_filter_video("720p") == {"720p"}

    def test_alias_4k(self) -> None:
        allowed = parse_format_filter_video("4k")
        assert allowed is not None
        assert "2160p" in allowed

    def test_multiple(self) -> None:
        allowed = parse_format_filter_video("1080p,720p,x265")
        assert allowed is not None
        assert "1080p" in allowed
        assert "720p" in allowed
        assert "x265" in allowed

    def test_invalid_ignored(self) -> None:
        allowed = parse_format_filter_video("1080p,invalid,720p")
        assert allowed == {"1080p", "720p"}


class TestMatchesFormatVideo:
    def test_none_allowed_accepts_any(self) -> None:
        info = parse_quality_video("Something 1080p")
        assert matches_format_video(info, None) is True
        info_unknown = parse_quality_video("No resolution here")
        assert matches_format_video(info_unknown, None) is True

    def test_allowed_kind(self) -> None:
        info = parse_quality_video("Title 1080p x264")
        assert matches_format_video(info, {"1080p"}) is True
        assert matches_format_video(info, {"720p"}) is False

    def test_allowed_codec(self) -> None:
        info = parse_quality_video("Title 1080p x265")
        assert matches_format_video(info, {"x265"}) is True
        assert matches_format_video(info, {"x264"}) is False

    def test_allowed_source(self) -> None:
        info = parse_quality_video("Title 1080p BluRay")
        assert matches_format_video(info, {"bluray"}) is True


class TestIsAcceptableVideo:
    def test_always_true(self) -> None:
        assert is_acceptable_video(parse_quality_video("")) is True
        assert is_acceptable_video(parse_quality_video("Anything 720p")) is True
