"""Helper para organizar downloads em subpastas conforme o tipo (Artist/Album, Movie, Show/Season)."""

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
    for sep in [" - ", " – ", " — ", " – ", " — "]:
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
