"""Integração Spotify: OAuth e listagem de playlists/faixas para gerar lista Artist - Track."""

from __future__ import annotations

import base64
import json
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

SCOPES = "playlist-read-private playlist-read-collaborative"


def _data_dir() -> Path:
    base = Path.home() / ".dl-torrent"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _tokens_path() -> Path:
    return _data_dir() / "spotify_tokens.json"


def get_authorize_url(client_id: str, redirect_uri: str, state: str | None = None) -> str:
    """URL para o usuário autorizar o app (abrir no navegador)."""
    state = state or secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    """
    Troca o code (callback) por access_token e refresh_token.
    Retorna dict com access_token, refresh_token, expires_in (segundos).
    """
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = requests.post(
        TOKEN_URL,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth}",
        },
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in", 3600),
    }


def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """
    Obtém novo access_token usando refresh_token.
    Retorna dict com access_token, expires_in. refresh_token pode ser reutilizado.
    """
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = requests.post(
        TOKEN_URL,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth}",
        },
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "access_token": data["access_token"],
        "expires_in": data.get("expires_in", 3600),
        "refresh_token": data.get("refresh_token") or refresh_token,
    }


def load_tokens() -> dict | None:
    """Carrega tokens do arquivo (~/.dl-torrent/spotify_tokens.json). Retorna None se não existir ou inválido."""
    path = _tokens_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("access_token") and data.get("refresh_token"):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_tokens(access_token: str, refresh_token: str, expires_in: int) -> None:
    """Salva tokens no arquivo. expires_at = now + expires_in - 60s de margem."""
    expires_at = time.time() + max(0, expires_in - 60)
    path = _tokens_path()
    path.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def ensure_valid_token(client_id: str, client_secret: str) -> str:
    """
    Retorna access_token válido: carrega do arquivo, refresh se expirado.
    Levanta RuntimeError se não houver tokens (usuário precisa rodar spotify login).
    """
    data = load_tokens()
    if not data:
        raise RuntimeError("Spotify não autenticado. Rode: dl-torrent spotify login")
    now = time.time()
    expires_at = data.get("expires_at") or 0
    if now >= expires_at:
        refreshed = refresh_access_token(
            data["refresh_token"],
            client_id,
            client_secret,
        )
        access_token = refreshed["access_token"]
        save_tokens(
            access_token,
            refreshed.get("refresh_token") or data["refresh_token"],
            refreshed["expires_in"],
        )
        return access_token
    return data["access_token"]


def _api_get(access_token: str, path: str, params: dict | None = None) -> dict:
    """GET request à API Spotify; retorna JSON. Levanta requests.HTTPError em erro."""
    url = f"{API_BASE}{path}" if path.startswith("/") else f"{API_BASE}/{path}"
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params or {},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_current_user_playlists(access_token: str, limit: int = 50) -> list[dict]:
    """
    Lista playlists do usuário (GET /v1/me/playlists). Pagina automaticamente.
    Cada item: id, name, owner, external_urls.spotify, etc.
    """
    out: list[dict] = []
    offset = 0
    while True:
        data = _api_get(
            access_token,
            "/me/playlists",
            params={"limit": min(50, limit), "offset": offset},
        )
        items = data.get("items") or []
        out.extend(items)
        if len(items) < 50 or len(out) >= limit:
            break
        offset += len(items)
    return out[:limit]


def get_playlist_tracks(playlist_id: str, access_token: str) -> list[dict]:
    """
    Lista faixas da playlist (GET /v1/playlists/{id}/tracks). Pagina automaticamente.
    Retorna lista de dicts com 'artist' (str, múltiplos artistas separados por ", ") e 'name' (track).
    Itens sem track (ex.: episódio) são ignorados.
    """
    out: list[dict] = []
    offset = 0
    limit = 50
    while True:
        data = _api_get(
            access_token,
            f"/playlists/{playlist_id}/tracks",
            params={"limit": limit, "offset": offset},
        )
        items = data.get("items") or []
        for it in items:
            track = it.get("track")
            if not track or not isinstance(track, dict):
                continue
            name = (track.get("name") or "").strip()
            if not name:
                continue
            artists = track.get("artists") or []
            artist_names = [
                (a.get("name") or "").strip()
                for a in artists
                if isinstance(a, dict) and (a.get("name") or "").strip()
            ]
            artist = ", ".join(artist_names) if artist_names else ""
            if artist:
                out.append({"artist": artist, "name": name})
        if len(items) < limit:
            break
        offset += len(items)
    return out
