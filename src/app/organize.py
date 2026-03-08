"""Helper para organizar downloads em subpastas conforme o tipo (Artist/Album, Movie, Show/Season).

Inclui funções de naming Plex-compatible para gerar paths completos com nomes de arquivo."""

from __future__ import annotations

import re
from typing import Literal

ContentType = Literal["music", "movies", "tv"]


def _sanitize(name: str, max_len: int = 80) -> str:
    """Remove caracteres inválidos para path e limita tamanho."""
    # Windows: \ / : * ? " < > |
    s = re.sub(r'[\\/:*?"<>|]', " ", name)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len] if s else "Unknown"


# ---------------------------------------------------------------------------
# Naming Plex-compatible (paths completos com nome de arquivo)
# ---------------------------------------------------------------------------

def plex_movie_folder(
    title: str,
    year: int | None = None,
    tmdb_id: int | None = None,
    imdb_id: str | None = None,
    include_tmdb: bool = True,
    include_imdb: bool = False,
) -> str:
    """
    Gera nome de pasta Plex-compatible para filme.
    Ex: 'Inception (2010) {tmdb-27205}' ou 'Inception (2010) {imdb-tt1375666}'
    """
    name = _sanitize(title.strip(), max_len=60) if title else "Unknown"
    parts = [name]
    if year:
        parts = [f"{name} ({year})"]
    ids = []
    if include_tmdb and tmdb_id:
        ids.append(f"{{tmdb-{tmdb_id}}}")
    if include_imdb and imdb_id:
        ids.append(f"{{{imdb_id}}}" if imdb_id.startswith("imdb-") else f"{{imdb-{imdb_id}}}")
    folder = " ".join(parts + ids)
    return _sanitize(folder, max_len=120)


def plex_movie_path(
    title: str,
    year: int | None = None,
    ext: str = ".mkv",
    tmdb_id: int | None = None,
    imdb_id: str | None = None,
    include_tmdb: bool = True,
    include_imdb: bool = False,
) -> str:
    """
    Gera path Plex-compatible completo para filme (pasta + arquivo).
    Ex: 'Inception (2010) {tmdb-27205}/Inception (2010).mkv'
    """
    folder = plex_movie_folder(title, year, tmdb_id, imdb_id, include_tmdb, include_imdb)
    name = _sanitize(title.strip(), max_len=60) if title else "Unknown"
    filename = f"{name} ({year}){ext}" if year else f"{name}{ext}"
    return f"{folder}/{_sanitize(filename, max_len=100)}"


def plex_tv_folder(
    show: str,
    year: int | None = None,
    tmdb_id: int | None = None,
    imdb_id: str | None = None,
    include_tmdb: bool = True,
    include_imdb: bool = False,
) -> str:
    """
    Gera nome de pasta raiz Plex-compatible para série.
    Ex: 'Breaking Bad {tmdb-1396}'
    """
    name = _sanitize(show.strip(), max_len=60) if show else "Unknown"
    ids = []
    if include_tmdb and tmdb_id:
        ids.append(f"{{tmdb-{tmdb_id}}}")
    if include_imdb and imdb_id:
        ids.append(f"{{{imdb_id}}}" if imdb_id.startswith("imdb-") else f"{{imdb-{imdb_id}}}")
    folder = " ".join([name] + ids)
    return _sanitize(folder, max_len=120)


def plex_tv_path(
    show: str,
    season: int,
    episode: int,
    episode_title: str | None = None,
    year: int | None = None,
    ext: str = ".mkv",
    tmdb_id: int | None = None,
    imdb_id: str | None = None,
    include_tmdb: bool = True,
    include_imdb: bool = False,
) -> str:
    """
    Gera path Plex-compatible completo para episódio de série.
    Ex: 'Breaking Bad {tmdb-1396}/Season 01/Breaking Bad - s01e01 - Pilot.mkv'
    """
    show_folder = plex_tv_folder(show, year, tmdb_id, imdb_id, include_tmdb, include_imdb)
    season_folder = f"Season {str(season).zfill(2)}"
    show_name = _sanitize(show.strip(), max_len=50) if show else "Unknown"
    ep_part = f"s{str(season).zfill(2)}e{str(episode).zfill(2)}"
    if episode_title:
        filename = f"{show_name} - {ep_part} - {_sanitize(episode_title, max_len=40)}{ext}"
    else:
        filename = f"{show_name} - {ep_part}{ext}"
    return f"{show_folder}/{season_folder}/{_sanitize(filename, max_len=120)}"


def plex_music_path(
    artist: str,
    album: str,
    year: int | None = None,
    track_number: int | None = None,
    track_title: str | None = None,
    ext: str = ".flac",
    disc_number: int | None = None,
    disc_total: int | None = None,
) -> str:
    """
    Gera path Plex-compatible completo para faixa de música.
    Ex: 'Pink Floyd/The Wall (1979)/01 - In the Flesh.flac'
    Multi-disco: 'Eric Clapton/Forever Man (2015)/d01 - 01 - Badge (Live).flac'
    """
    artist_name = _sanitize(artist.strip(), max_len=60) if artist and artist.strip() else "Unknown Artist"
    album_name = _sanitize(album.strip(), max_len=60) if album and album.strip() else "Unknown Album"

    if artist_name == "Unknown Artist" and album_name == "Unknown Album" and track_title:
        album_name = _sanitize(track_title.strip(), max_len=60)

    album_folder = f"{album_name} ({year})" if year else album_name

    use_disc_prefix = disc_number is not None and (
        (disc_total is not None and disc_total > 1)
        or (disc_number > 1)
    )

    if track_number and track_title:
        track_part = f"{str(track_number).zfill(2)} - {_sanitize(track_title, max_len=60)}{ext}"
    elif track_title:
        track_part = f"{_sanitize(track_title, max_len=60)}{ext}"
    else:
        track_part = f"track{ext}"

    if use_disc_prefix:
        filename = f"d{str(disc_number).zfill(2)} - {track_part}"
    else:
        filename = track_part

    return f"{artist_name}/{album_folder}/{filename}"


def extract_movie_subpath(title: str) -> str:
    """
    Extrai subpath para filme: 'Movie Name (Year)' ou 'Movies/Movie Name (Year)'.
    Padrões: "Name (YYYY)", "Name YYYY", "Name - YYYY"; remove tags [1080p], etc.
    """
    if not title or not title.strip():
        return "Unknown"
    t = title.strip()
    # Remover tags comuns no final [1080p], [x265], [BluRay], etc.
    t = re.sub(r"\s*\[[^\]]*\]\s*$", "", t)
    # Ano entre parênteses: "Movie Name (2020)"
    m = re.search(r"^(.+?)\s*\((\d{4})\)\s*$", t)
    if m:
        name, year = m.group(1).strip(), m.group(2)
        return _sanitize(f"{name} ({year})")
    # Ano separado: "Movie Name 2020" ou "Movie Name - 2020"
    m = re.search(r"^(.+?)\s+[-.]?\s*(\d{4})\s*$", t)
    if m:
        name, year = m.group(1).strip(), m.group(2)
        return _sanitize(f"{name} ({year})")
    return _sanitize(t[:60])


def extract_tv_subpath(title: str) -> str:
    """
    Extrai subpath para série: 'Show Name/Season 01' ou 'Show Name/Season 01/S01E05 - Episode'.
    Detecta S01, Season 1, S01E05, etc.
    """
    if not title or not title.strip():
        return "Unknown"
    t = title.strip()
    # Remover tags no final [1080p], etc.
    t = re.sub(r"\s*\[[^\]]*\]\s*$", "", t)
    # S01E05 ou S1E5
    m = re.search(r"^(.+?)[\s.-]+(S\d{1,2})E(\d{1,2})", t, re.I)
    if m:
        show = _sanitize(m.group(1).strip())
        s_num = m.group(2).upper()
        if len(s_num) == 2:  # S1 -> S01
            s_num = "S" + s_num[1:].zfill(2)
        season_folder = f"Season {s_num[1:].lstrip('0') or '1'}"
        return f"{show}/{season_folder}"
    # Season 1 ou Season 01
    m = re.search(r"^(.+?)[\s.-]+Season\s*(\d{1,2})", t, re.I)
    if m:
        show = _sanitize(m.group(1).strip())
        season_num = m.group(2).lstrip("0") or "1"
        return f"{show}/Season {season_num}"
    # S01 ou S1 sozinho
    m = re.search(r"^(.+?)[\s.-]+(S\d{1,2})\b", t, re.I)
    if m:
        show = _sanitize(m.group(1).strip())
        s_num = m.group(2).upper()[1:].lstrip("0") or "1"
        return f"{show}/Season {s_num}"
    return _sanitize(t[:50])


def extract_subpath_by_content_type(title: str, content_type: ContentType) -> str:
    """Retorna o subpath conforme o tipo: music -> Artist/Album, movies -> Movie (Year), tv -> Show/Season."""
    if content_type == "movies":
        return extract_movie_subpath(title)
    if content_type == "tv":
        return extract_tv_subpath(title)
    return extract_artist_album_subpath(title)


def extract_artist_album_subpath(title: str) -> str:
    """
    Extrai um subpath 'Artist/Album' do título do torrent.
    Títulos típicos: "Artist - Album (Year) [FLAC]", "Artist – Album", "Artist - Album".
    Retorna path sanitizado; se não conseguir extrair, usa os primeiros caracteres do título.
    """
    if not title or not title.strip():
        return "Unknown"
    t = title.strip()
    # Separadores comuns: " - ", " – ", " — "
    for sep in [" - ", " – ", " — "]:
        if sep in t:
            parts = t.split(sep, 1)
            artist = _sanitize(parts[0].strip()) if parts else ""
            rest = parts[1].strip() if len(parts) > 1 else ""
            # Remover sufixos comuns [FLAC], (Year), etc.
            rest = re.sub(r"\s*\[[^\]]*\]\s*$", "", rest)
            rest = re.sub(r"\s*\(\d{4}\)\s*$", "", rest)
            album = _sanitize(rest) if rest else _sanitize(t[:50])
            if artist and album:
                return f"{artist}/{album}"
            if artist:
                return artist
            if album:
                return album
    return _sanitize(t[:50])
