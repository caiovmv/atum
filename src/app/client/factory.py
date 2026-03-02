"""Factory do cliente de torrent conforme config (registry: aberto para extensão)."""

from __future__ import annotations

from typing import Callable

from ..config import Settings
from .base import TorrentClient
from .folder import FolderClient
from .transmission import TransmissionClient
from .utorrent import UTorrentClient

# Registry: client_type -> função (kwargs) -> TorrentClient. Novos clientes só precisam se registrar.
_CLIENT_REGISTRY: dict[str, Callable[..., TorrentClient]] = {}


def _register(name: str):
    def decorator(fn: Callable[..., TorrentClient]):
        _CLIENT_REGISTRY[name] = fn
        return fn
    return decorator


@_register("transmission")
def _make_transmission(
    *,
    transmission_host: str = "localhost",
    transmission_port: int = 9091,
    transmission_user: str = "",
    transmission_password: str = "",
    transmission_download_dir: str = "",
    **_: object,
) -> TorrentClient:
    return TransmissionClient(
        host=transmission_host,
        port=transmission_port,
        user=transmission_user,
        password=transmission_password,
        download_dir=transmission_download_dir or None,
    )


@_register("utorrent")
def _make_utorrent(
    *,
    utorrent_url: str = "http://localhost:8080",
    utorrent_user: str = "admin",
    utorrent_password: str = "",
    **_: object,
) -> TorrentClient:
    return UTorrentClient(
        base_url=utorrent_url,
        user=utorrent_user,
        password=utorrent_password,
    )


@_register("folder")
def _make_folder(
    *,
    watch_folder: str = "./torrents",
    **_: object,
) -> TorrentClient:
    return FolderClient(watch_folder=watch_folder)


def create_client_from_settings(settings: Settings) -> TorrentClient:
    """Cria um TorrentClient a partir das configurações (evita duplicar kwargs em search/feeds)."""
    return get_client(
        settings.client_type,
        transmission_host=settings.transmission_host,
        transmission_port=settings.transmission_port,
        transmission_user=settings.transmission_user,
        transmission_password=settings.transmission_password,
        transmission_download_dir=settings.download_dir or "",
        utorrent_url=settings.utorrent_url,
        utorrent_user=settings.utorrent_user,
        utorrent_password=settings.utorrent_password,
        watch_folder=settings.watch_folder,
    )


def get_client(
    client_type: str,
    *,
    transmission_host: str = "localhost",
    transmission_port: int = 9091,
    transmission_user: str = "",
    transmission_password: str = "",
    transmission_download_dir: str = "",
    utorrent_url: str = "http://localhost:8080",
    utorrent_user: str = "admin",
    utorrent_password: str = "",
    watch_folder: str = "./torrents",
) -> TorrentClient:
    if client_type not in _CLIENT_REGISTRY:
        raise ValueError(f"Cliente desconhecido: {client_type}")
    return _CLIENT_REGISTRY[client_type](
        transmission_host=transmission_host,
        transmission_port=transmission_port,
        transmission_user=transmission_user,
        transmission_password=transmission_password,
        transmission_download_dir=transmission_download_dir,
        utorrent_url=utorrent_url,
        utorrent_user=utorrent_user,
        utorrent_password=utorrent_password,
        watch_folder=watch_folder,
    )
