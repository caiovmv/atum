"""Testes do parser de qualidade (quality.py)."""

from __future__ import annotations

import pytest

from app.quality import (
    QualityInfo,
    QualityScore,
    is_acceptable,
    matches_format,
    parse_format_filter,
    parse_quality,
)


class TestParseQuality:
    """Testes de parse_quality."""

    def test_empty_returns_unknown(self) -> None:
        assert parse_quality("").kind == "unknown"
        assert parse_quality("   ").kind == "unknown"
        assert parse_quality("").score == QualityScore.UNKNOWN

    def test_flac_detected(self) -> None:
        info = parse_quality("Artist - Album [FLAC] 2024")
        assert info.kind == "flac"
        assert info.score == QualityScore.FLAC
        assert info.label == "FLAC"

    def test_flac_case_insensitive(self) -> None:
        assert parse_quality("Album Flac 24bit").kind == "flac"
        assert parse_quality("album FLAC").kind == "flac"

    def test_alac_detected(self) -> None:
        info = parse_quality("Artist - Album ALAC m4a")
        assert info.kind == "alac"
        assert info.score == QualityScore.ALAC
        assert info.label == "ALAC"

    def test_mp3_320_detected(self) -> None:
        info = parse_quality("Album Mp3 320kbps")
        assert info.kind == "mp3_320"
        assert info.score == QualityScore.MP3_320
        assert info.bitrate_kbps == 320
        assert info.label == "MP3 320"

    def test_mp3_320_cbr(self) -> None:
        assert parse_quality("Album CBR 320").kind == "mp3_320"

    def test_mp3_acceptable_v0(self) -> None:
        info = parse_quality("Album V0 VBR")
        assert info.kind == "mp3_acceptable"
        assert info.score == QualityScore.MP3_ACCEPTABLE
        assert info.bitrate_kbps == 245

    def test_mp3_192_acceptable(self) -> None:
        info = parse_quality("Album MP3 192kbps")
        assert info.kind == "mp3_acceptable"
        assert info.bitrate_kbps in (192, None)
        assert "192" in info.label or "MP3" in info.label

    def test_mp3_256_acceptable(self) -> None:
        info = parse_quality("Album 256 kbps")
        assert info.kind == "mp3_acceptable"
        assert info.bitrate_kbps == 256

    def test_mp3_198_acceptable(self) -> None:
        info = parse_quality("Album 198k")
        assert info.kind == "mp3_acceptable"
        assert info.bitrate_kbps == 198

    def test_mp3_128_rejected(self) -> None:
        info = parse_quality("Album 128kbps")
        assert info.kind == "unknown"
        assert info.score == QualityScore.UNKNOWN

    def test_mp3_generic_acceptable(self) -> None:
        info = parse_quality("Album MP3")
        assert info.kind == "mp3_acceptable"
        assert info.score == QualityScore.MP3_ACCEPTABLE

    def test_unknown_when_no_match(self) -> None:
        assert parse_quality("Random Title 2024").kind == "unknown"
        assert parse_quality("WAV 24bit").kind == "unknown"


class TestIsAcceptable:
    """Testes de is_acceptable."""

    def test_flac_acceptable(self) -> None:
        assert is_acceptable(parse_quality("FLAC")) is True

    def test_mp3_320_acceptable(self) -> None:
        assert is_acceptable(parse_quality("320")) is True

    def test_mp3_192_acceptable(self) -> None:
        assert is_acceptable(parse_quality("Album MP3 192kbps")) is True

    def test_unknown_not_acceptable(self) -> None:
        assert is_acceptable(parse_quality("128kbps")) is False
        assert is_acceptable(parse_quality("Random")) is False


class TestParseFormatFilter:
    """Testes de parse_format_filter."""

    def test_none_or_empty_returns_none(self) -> None:
        assert parse_format_filter(None) is None
        assert parse_format_filter("") is None
        assert parse_format_filter("   ") is None

    def test_single_kind(self) -> None:
        assert parse_format_filter("flac") == {"flac"}
        assert parse_format_filter("alac") == {"alac"}

    def test_alias_320(self) -> None:
        assert parse_format_filter("320") == {"mp3_320"}

    def test_alias_mp3(self) -> None:
        assert parse_format_filter("mp3") == {"mp3_acceptable"}

    def test_multiple(self) -> None:
        assert parse_format_filter("flac,alac,320") == {"flac", "alac", "mp3_320"}

    def test_invalid_ignored(self) -> None:
        assert parse_format_filter("flac,invalid,320") == {"flac", "mp3_320"}


class TestMatchesFormat:
    """Testes de matches_format."""

    def test_none_allowed_accepts_acceptable(self) -> None:
        assert matches_format(parse_quality("FLAC"), None) is True
        assert matches_format(parse_quality("320"), None) is True
        assert matches_format(parse_quality("128"), None) is False

    def test_allowed_kind(self) -> None:
        flac_info = parse_quality("FLAC")
        assert matches_format(flac_info, {"flac"}) is True
        assert matches_format(flac_info, {"alac", "mp3_320"}) is False

    def test_unacceptable_fails_even_if_in_allowed(self) -> None:
        unknown = parse_quality("WAV")
        assert matches_format(unknown, {"flac", "alac"}) is False
