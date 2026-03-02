"""Interface comum para clientes de torrent."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TorrentClient(ABC):
    """Interface para adicionar torrent (magnet ou URL .torrent)."""

    @abstractmethod
    def add(self, magnet_or_url: str) -> bool:
        """Adiciona o torrent. Retorna True se ok."""
        ...
