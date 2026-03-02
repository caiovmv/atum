"""Testes do helper organize (Artist/Album, Movie, TV a partir do título)."""

from __future__ import annotations

import pytest

from app.organize import (
    extract_artist_album_subpath,
    extract_movie_subpath,
    extract_subpath_by_content_type,
    extract_tv_subpath,
)


class TestExtractArtistAlbumSubpath:
    def test_empty_returns_unknown(self) -> None:
        assert extract_artist_album_subpath("") == "Unknown"
        assert extract_artist_album_subpath("   ") == "Unknown"

    def test_artist_dash_album(self) -> None:
        assert extract_artist_album_subpath("Pink Floyd - The Wall") == "Pink Floyd/The Wall"

    def test_artist_dash_album_with_year_and_flac(self) -> None:
        assert extract_artist_album_subpath("Artist - Album (2020) [FLAC]") == "Artist/Album"
        assert extract_artist_album_subpath("Band - Title (1999) [MP3 320]") == "Band/Title"

    def test_unicode_separator(self) -> None:
        # – (en dash) e — (em dash)
        assert "Artist" in extract_artist_album_subpath("Artist – Album")
        assert "Album" in extract_artist_album_subpath("Artist – Album")

    def test_no_separator_returns_sanitized_title_prefix(self) -> None:
        result = extract_artist_album_subpath("SomeRandomTitleNoSeparator")
        assert "/" not in result
        assert "SomeRandomTitleNoSeparator" == result or result == "Unknown"

    def test_sanitizes_invalid_path_chars(self) -> None:
        result = extract_artist_album_subpath("Artist - Album: Subtitle * invalid")
        assert ":" not in result
        assert "*" not in result
        assert "Artist" in result and "Album" in result

    def test_only_artist_returns_artist(self) -> None:
        # "Artist - " com resto vazio após strip
        result = extract_artist_album_subpath("Pink Floyd - ")
        assert "Pink Floyd" in result


class TestExtractMovieSubpath:
    def test_empty_returns_unknown(self) -> None:
        assert extract_movie_subpath("") == "Unknown"
        assert extract_movie_subpath("   ") == "Unknown"

    def test_name_year_parentheses(self) -> None:
        assert extract_movie_subpath("Movie Name (2020)") == "Movie Name (2020)"
        assert extract_movie_subpath("Another Film (1999) [1080p]") == "Another Film (1999)"

    def test_name_year_separate(self) -> None:
        result = extract_movie_subpath("Movie Name 2020")
        assert "2020" in result
        assert "Movie Name" in result

    def test_no_year_returns_sanitized_prefix(self) -> None:
        result = extract_movie_subpath("Some Movie Title Without Year")
        assert result != "Unknown"
        assert "Some" in result or "Movie" in result


class TestExtractTvSubpath:
    def test_empty_returns_unknown(self) -> None:
        assert extract_tv_subpath("") == "Unknown"

    def test_s01e05_pattern(self) -> None:
        result = extract_tv_subpath("Show Name S01E05 - Episode Title")
        assert "Show Name" in result
        assert "Season" in result

    def test_season_1_pattern(self) -> None:
        result = extract_tv_subpath("Show Name Season 1")
        assert "Show Name" in result
        assert "Season" in result

    def test_s01_standalone(self) -> None:
        result = extract_tv_subpath("Show Name S01")
        assert "Show Name" in result
        assert "Season" in result


class TestExtractSubpathByContentType:
    def test_music_uses_artist_album(self) -> None:
        result = extract_subpath_by_content_type("Artist - Album", "music")
        assert "Artist" in result
        assert "Album" in result

    def test_movies_uses_movie_subpath(self) -> None:
        result = extract_subpath_by_content_type("Movie Name (2020)", "movies")
        assert "Movie Name" in result
        assert "2020" in result

    def test_tv_uses_tv_subpath(self) -> None:
        result = extract_subpath_by_content_type("Show Name S01E05", "tv")
        assert "Show Name" in result
        assert "Season" in result
