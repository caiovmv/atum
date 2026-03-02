"""Integração Last.fm: resolver nome de álbum/artista para query de busca."""

from __future__ import annotations

import urllib.parse

import requests

BASE_URL = "https://ws.audioscrobbler.com/2.0/"


def resolve_album(album: str, api_key: str, limit: int = 10) -> list[dict]:
    """
    Busca álbum no Last.fm; retorna lista de dicts com 'artist' e 'name' (álbum).
    Requer api_key (obtenha em https://www.last.fm/api/account).
    """
    if not api_key or not (album or "").strip():
        return []
    album = album.strip()
    try:
        r = requests.get(
            BASE_URL,
            params={
                "method": "album.search",
                "album": album,
                "api_key": api_key,
                "format": "json",
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        matches = (data.get("results") or {}).get("albummatches") or {}
        albums = matches.get("album") or []
        if isinstance(albums, dict):
            albums = [albums]
        out = []
        for a in albums[:limit]:
            artist = (a.get("artist") or "").strip()
            name = (a.get("name") or "").strip()
            if artist and name:
                out.append({"artist": artist, "name": name})
        return out
    except Exception:
        return []


def resolve_artist_album(artist: str, album: str, api_key: str) -> str | None:
    """
    Dado artista e álbum, retorna string 'Artist - Album' (canonizada pelo Last.fm se possível).
    Se a API falhar, retorna f'{artist} - {album}'.
    """
    artist = (artist or "").strip()
    album = (album or "").strip()
    if not artist and not album:
        return None
    if not artist:
        # Só álbum: usar album.search e pegar o primeiro
        results = resolve_album(album, api_key, limit=1)
        if results:
            r = results[0]
            return f"{r['artist']} - {r['name']}"
        return album
    if not album:
        return artist
    # Ambos: retornar "Artist - Album" (opcionalmente validar com album.getInfo)
    try:
        r = requests.get(
            BASE_URL,
            params={
                "method": "album.getInfo",
                "artist": artist,
                "album": album,
                "api_key": api_key,
                "format": "json",
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        alb = data.get("album") or {}
        a = (alb.get("artist") or {}).get("name") or artist
        n = alb.get("name") or album
        return f"{a} - {n}"
    except Exception:
        return f"{artist} - {album}"


def get_chart_tracks(api_key: str, limit: int = 50, page: int = 1) -> list[dict]:
    """
    Top tracks do Last.fm (chart.getTopTracks).
    Retorna lista de dicts com 'artist' e 'name' (nome da faixa).
    """
    if not (api_key or "").strip():
        return []
    try:
        r = requests.get(
            BASE_URL,
            params={
                "method": "chart.getTopTracks",
                "api_key": api_key.strip(),
                "format": "json",
                "limit": min(50, max(1, limit)),
                "page": max(1, page),
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        tracks = (data.get("tracks") or {}).get("track") or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        out = []
        for t in tracks:
            artist = (t.get("artist") or {})
            if isinstance(artist, dict):
                artist = (artist.get("name") or "").strip()
            else:
                artist = (artist or "").strip()
            name = (t.get("name") or "").strip()
            if artist and name:
                out.append({"artist": artist, "name": name})
        return out
    except Exception:
        return []
