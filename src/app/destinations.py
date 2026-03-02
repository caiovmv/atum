"""Estratégias de destino do magnet (Strategy): watch folder, client, direct, background."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .client import get_client
from .config import Settings, get_settings
from .download_manager import add as download_add
from .download_manager import start as download_start
from .organize import ContentType, extract_subpath_by_content_type


class MagnetDestination(Protocol):
    """Interface para enviar magnet a um destino (cliente, pasta, fila, download direto)."""

    def send(self, magnet: str, title: str) -> tuple[bool, str | None]:
        """
        Envia o magnet ao destino.
        Retorna (ok, error_message). error_message é preenchido em caso de falha.
        """
        ...

    def run_after_if_sync(self, progress_callback=None) -> None:
        """Se for download direto síncrono, executa run_until_complete. Senão, no-op."""
        ...

    def success_message(self, ok: int, fail: int) -> str:
        """Mensagem final quando ok > 0."""
        ...

    def failure_message(self) -> str:
        """Mensagem quando ok == 0 e fail > 0."""
        ...


class WatchFolderDestination:
    def __init__(self, folder: str) -> None:
        self._client = get_client("folder", watch_folder=folder)

    def send(self, magnet: str, title: str) -> tuple[bool, str | None]:
        if self._client.add(magnet):
            return True, None
        return False, getattr(self._client, "_last_error", None)

    def run_after_if_sync(self, progress_callback=None) -> None:
        pass

    def success_message(self, ok: int, fail: int) -> str:
        return f"{ok} magnet(s) salvo(s) na pasta." + (f" {fail} falha(s)." if fail else "")

    def failure_message(self) -> str:
        return "Nenhum magnet foi salvo. Verifique o caminho da pasta."


class ClientDestination:
    def __init__(self, settings: Settings) -> None:
        from .client import create_client_from_settings
        self._client = create_client_from_settings(settings)

    def send(self, magnet: str, title: str) -> tuple[bool, str | None]:
        if self._client.add(magnet):
            return True, None
        return False, getattr(self._client, "_last_error", None)

    def run_after_if_sync(self, progress_callback=None) -> None:
        pass

    def success_message(self, ok: int, fail: int) -> str:
        return f"{ok} torrent(s) adicionado(s) ao cliente." + (f" {fail} falha(s)." if fail else "")

    def failure_message(self) -> str:
        return "Nenhum torrent foi adicionado ao cliente. Use --save-to-watch-folder ou --download-direct, ou verifique TRANSMISSION_* / UTORRENT_* / WATCH_FOLDER."


class BackgroundQueueDestination:
    def __init__(
        self,
        path: str,
        organize_by_artist_album: bool = False,
        content_type: ContentType = "music",
    ) -> None:
        self._path = path
        self._organize = organize_by_artist_album
        self._content_type = content_type

    def send(self, magnet: str, title: str) -> tuple[bool, str | None]:
        save_path = self._path
        if self._organize and title:
            subpath = extract_subpath_by_content_type(title, self._content_type)
            save_path = str(Path(self._path) / subpath)
        did = download_add(magnet, save_path, title, content_type=self._content_type)
        if did > 0:
            download_start(did)
            return True, None
        return False, None

    def run_after_if_sync(self, progress_callback=None) -> None:
        pass

    def success_message(self, ok: int, fail: int) -> str:
        return f"{ok} download(s) em background. Use 'dl-torrent download list' para acompanhar." + (f" {fail} falha(s)." if fail else "")

    def failure_message(self) -> str:
        return "Nenhum torrent foi baixado. Verifique --download-dir ou instale: pip install torrentp."


class DirectDownloadDestination:
    """Download direto síncrono (LibtorrentDirectClient)."""

    def __init__(
        self,
        path: str,
        port: int | None = None,
        organize_by_artist_album: bool = False,
        content_type: ContentType = "music",
    ) -> None:
        from .client.libtorrent_direct import LibtorrentDirectClient
        self._client = LibtorrentDirectClient(save_path=path, port=port)
        self._base_path = Path(path).expanduser().resolve()
        self._organize = organize_by_artist_album
        self._content_type = content_type

    def send(self, magnet: str, title: str) -> tuple[bool, str | None]:
        save_path_override = None
        if self._organize and title:
            subpath = extract_subpath_by_content_type(title, self._content_type)
            save_path_override = str(self._base_path / subpath)
        if self._client.add(magnet, save_path_override=save_path_override):
            return True, None
        return False, getattr(self._client, "_last_error", None)

    def run_after_if_sync(self, progress_callback=None) -> None:
        self._client.run_until_complete(progress_callback=progress_callback)

    def success_message(self, ok: int, fail: int) -> str:
        return f"{ok} torrent(s) baixado(s) diretamente." + (f" {fail} falha(s)." if fail else "")

    def failure_message(self) -> str:
        return "Nenhum torrent foi baixado. Verifique --download-dir ou instale: pip install torrentp."


def resolve_destination(
    *,
    save_to_watch_folder: bool = False,
    watch_folder_path: str | None = None,
    download_direct: bool = False,
    download_direct_path: str | None = None,
    download_direct_port: int | None = None,
    download_background: bool = False,
    organize_by_artist_album: bool = False,
    content_type: ContentType = "music",
    settings: Settings | None = None,
) -> MagnetDestination:
    """Resolve o destino dos magnets a partir das opções (Strategy)."""
    s = settings or get_settings()
    path = (download_direct_path or getattr(s, "download_dir", "") or s.watch_folder or "./downloads").strip()
    organize = organize_by_artist_album or getattr(s, "organize_by_artist_album", False)

    if save_to_watch_folder:
        folder = (watch_folder_path or getattr(s, "watch_folder", "") or "./torrents").strip()
        return WatchFolderDestination(folder)
    if download_direct and download_background:
        return BackgroundQueueDestination(path, organize_by_artist_album=organize, content_type=content_type)
    if download_direct:
        try:
            return DirectDownloadDestination(
                path,
                port=download_direct_port,
                organize_by_artist_album=organize,
                content_type=content_type,
            )
        except ImportError as e:
            raise RuntimeError(
                "Erro: --download-direct requer torrentp (pip install torrentp). "
                f"Alternativa: use --save-to-watch-folder. Detalhes: {e}"
            ) from e
    return ClientDestination(s)
