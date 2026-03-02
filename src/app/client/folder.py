"""Cliente 'pasta': salva magnets em arquivo para FrostWire/pasta monitorada."""

from __future__ import annotations

from pathlib import Path

from .base import TorrentClient


class FolderClient(TorrentClient):
    """Escreve magnet links em arquivo na pasta configurada (ex.: para FrostWire)."""

    def __init__(self, watch_folder: str | Path) -> None:
        self._folder = Path(watch_folder).expanduser().resolve()
        self._folder.mkdir(parents=True, exist_ok=True)
        self._magnets_file = self._folder / "magnets.txt"
        self._last_error: str | None = None

    def add(self, magnet_or_url: str) -> bool:
        self._last_error = None
        if not magnet_or_url.strip():
            self._last_error = "Link vazio."
            return False
        try:
            with open(self._magnets_file, "a", encoding="utf-8") as f:
                f.write(magnet_or_url.strip() + "\n")
            return True
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            return False
