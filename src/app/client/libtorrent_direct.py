"""Download direto via libtorrent (DHT, trackers, porta). Sem fallback TorrentP."""

from __future__ import annotations

import os
from pathlib import Path


def _default_port() -> int:
    """Porta diferente por processo para permitir vários downloads em paralelo (outros terminais)."""
    return 6881 + (os.getpid() % 500)


class LibtorrentDirectClient:
    """
    Baixa torrents diretamente para uma pasta.
    add() enfileira o magnet/.torrent; run_until_complete() baixa todos em sequência.
    """

    def __init__(self, save_path: str | Path, port: int | None = None) -> None:
        try:
            from .libtorrent_engine import run_download  # noqa: F401
        except ImportError as e:
            msg = str(e).strip()
            if "DLL" in msg or "libtorrent" in msg.lower():
                raise ImportError(
                    "libtorrent não pôde ser carregado (falta DLL no Windows?). "
                    "Instale: pip install libtorrent-windows-dll. Diagnóstico: python scripts/debug_libtorrent.py."
                ) from e
            raise ImportError(
                "Download requer libtorrent. Instale: pip install libtorrent. Diagnóstico: python scripts/debug_libtorrent.py."
            ) from e
        self._save_path = Path(save_path).expanduser().resolve()
        self._save_path.mkdir(parents=True, exist_ok=True)
        self._port = port if port is not None else _default_port()
        self._magnets = []  # (magnet_or_url, save_path_override)
        self._last_error = None

    def add(self, magnet_or_url: str, save_path_override: str | Path | None = None) -> bool:
        if not magnet_or_url or not magnet_or_url.strip():
            return False
        magnet_or_url = magnet_or_url.strip()
        if magnet_or_url.startswith("magnet:") or magnet_or_url.endswith(".torrent") or Path(magnet_or_url).exists():
            path = str(save_path_override) if save_path_override is not None else None
            self._magnets.append((magnet_or_url, path))
            return True
        self._last_error = "Só magnet ou arquivo .torrent são suportados"
        return False

    def run_until_complete(self, progress_callback=None) -> None:
        """Baixa em sequência cada magnet/.torrent enfileirado."""
        if not self._magnets:
            return
        try:
            from rich.console import Console
            has_rich = True
        except ImportError:
            has_rich = False
        console = Console() if has_rich else None
        n = len(self._magnets)
        from .libtorrent_engine import run_download
        port = self._port
        for i, item in enumerate(self._magnets):
            link = item[0] if isinstance(item, tuple) else item
            path_override = item[1] if isinstance(item, tuple) and len(item) > 1 else None
            save_str = str(Path(path_override).expanduser().resolve()) if path_override else str(self._save_path)
            Path(save_str).mkdir(parents=True, exist_ok=True)
            current = i + 1
            if has_rich and console:
                console.print(f"\n[bold blue]Download [{current}/{n}][/bold blue] Iniciando…")
            elif progress_callback:
                progress_callback(0.0, i, n)
            try:
                success, _ = run_download(link, save_str, port, progress_interval_seconds=1.0)
                if not success:
                    self._last_error = "Download falhou ou foi interrompido"
                    if has_rich and console:
                        console.print(f"[red]  ✗ Erro[/red]")
                    continue
            except Exception as e:
                self._last_error = f"{type(e).__name__}: {e}"
                if has_rich and console:
                    console.print(f"[red]  ✗ Erro: {e}[/red]")
                continue
            if has_rich and console:
                console.print(f"[green]  ✓ [{current}/{n}] Concluído.[/green]")
            if progress_callback:
                progress_callback(current / n, current, n)
            port = port + 1  # porta diferente por torrent em sequência
        if has_rich and console and n > 0:
            console.print(f"\n[bold green]Download direto concluído: {n} torrent(s)[/bold green]")
