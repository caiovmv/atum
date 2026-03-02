"""Cliente Transmission via transmission-rpc."""

from __future__ import annotations

from .base import TorrentClient


class TransmissionClient(TorrentClient):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9091,
        user: str = "",
        password: str = "",
        download_dir: str = "",
    ) -> None:
        self._host = host
        self._port = port
        self._user = user or None
        self._password = password or None
        self._download_dir = download_dir or None
        self._last_error: str | None = None

    def add(self, magnet_or_url: str) -> bool:
        self._last_error = None
        try:
            from transmission_rpc import Client

            c = Client(
                host=self._host,
                port=self._port,
                username=self._user,
                password=self._password,
            )
            kwargs = {}
            if self._download_dir:
                kwargs["download_dir"] = self._download_dir
            c.add_torrent(magnet_or_url, **kwargs)
            return True
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            return False
