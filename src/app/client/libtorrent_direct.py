"""Download direto via TorrentP (magnet ou .torrent) para uma pasta."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path


def _default_port() -> int:
    """Porta diferente por processo para permitir vários downloads em paralelo (outros terminais)."""
    return 6881 + (os.getpid() % 500)


class LibtorrentDirectClient:
    """
    Baixa torrents diretamente para uma pasta usando TorrentP.
    add() enfileira o magnet; run_until_complete() baixa todos em sequência.
    """

    def __init__(self, save_path: str | Path, port: int | None = None) -> None:
        self._save_path = Path(save_path).expanduser().resolve()
        self._save_path.mkdir(parents=True, exist_ok=True)
        self._port = port if port is not None else _default_port()
        self._magnets: list[tuple[str, str | None]] = []  # (magnet_or_url, save_path_override)
        self._last_error: str | None = None
        # Falha logo se TorrentP não estiver disponível
        try:
            from torrentp import TorrentDownloader  # noqa: F401
        except ImportError as e:
            msg = str(e).strip()
            if "DLL" in msg or "libtorrent" in msg.lower():
                raise ImportError(
                    "TorrentP não pôde ser carregado (falta DLL no Windows?). "
                    "Instale as DLLs OpenSSL: pip install libtorrent-windows-dll. "
                    "Depois tente de novo. Diagnóstico: python scripts/debug_libtorrent.py. "
                    "Alternativa: use --save-to-watch-folder para salvar os magnets."
                ) from e
            raise ImportError(
                "Download direto requer TorrentP. Instale com: pip install torrentp"
            ) from e

    def add(self, magnet_or_url: str, save_path_override: str | Path | None = None) -> bool:
        if not magnet_or_url or not magnet_or_url.strip():
            return False
        magnet_or_url = magnet_or_url.strip()
        # Aceita magnet ou caminho para .torrent
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
        from torrentp import TorrentDownloader

        try:
            from rich.console import Console
            has_rich = True
        except ImportError:
            has_rich = False

        save_str = str(self._save_path)
        n = len(self._magnets)
        console = Console() if has_rich else None

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
                downloader = TorrentDownloader(link, save_str, port=self._port)
                asyncio.run(downloader.start_download())
            except Exception as e:
                self._last_error = f"{type(e).__name__}: {e}"
                if has_rich and console:
                    console.print(f"[red]  ✗ Erro: {e}[/red]")
                continue

            if has_rich and console:
                console.print(f"[green]  ✓ [{current}/{n}] Concluído.[/green]")
            if progress_callback:
                progress_callback(current / n, current, n)

        if has_rich and console and n > 0:
            console.print(f"\n[bold green]Download direto concluído: {n} torrent(s) em {save_str}[/bold green]")
