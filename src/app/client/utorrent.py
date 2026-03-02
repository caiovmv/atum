"""Cliente uTorrent via Web API."""

from __future__ import annotations

import re
from urllib.parse import urljoin

import requests

from .base import TorrentClient


class UTorrentClient(TorrentClient):
    """uTorrent Web UI API (token + add torrent)."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        user: str = "admin",
        password: str = "",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = (user, password) if (user or password) else None
        self._session = requests.Session()
        if self._auth:
            self._session.auth = self._auth

    def _get_token(self) -> str | None:
        try:
            r = self._session.get(
                urljoin(self._base_url + "/", "token.html"),
                timeout=10,
            )
            r.raise_for_status()
            # Resposta é HTML com <div id="token">TOKEN</div>
            m = re.search(r'<div\s+id="token"[^>]*>([^<]+)</div>', r.text)
            if m:
                return m.group(1).strip()
            return None
        except Exception:
            return None

    def add(self, magnet_or_url: str) -> bool:
        self._last_error = None
        token = self._get_token()
        if not token:
            self._last_error = "Não foi possível obter token do uTorrent (verifique URL/porta)."
            return False
        try:
            if magnet_or_url.startswith("magnet:"):
                r = self._session.get(
                    urljoin(self._base_url + "/", "gui/"),
                    params={"action": "add-url", "s": magnet_or_url, "token": token},
                    timeout=15,
                )
            else:
                # URL de .torrent: baixar e enviar como add-file
                resp = self._session.get(magnet_or_url, timeout=15)
                resp.raise_for_status()
                files = {"torrent_file": ("file.torrent", resp.content)}
                r = self._session.post(
                    urljoin(self._base_url + "/", "gui/"),
                    data={"action": "add-file", "token": token},
                    files=files,
                    timeout=15,
                )
            r.raise_for_status()
            return True
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            return False
