"""Clientes de torrent (Transmission, uTorrent, pasta)."""

from .base import TorrentClient
from .factory import create_client_from_settings, get_client

__all__ = ["TorrentClient", "create_client_from_settings", "get_client"]
