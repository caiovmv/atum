"""Worker que roda em thread ou subprocesso para um download (libtorrent direto ou TorrentP fallback). Atualiza status no DB."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from threading import Event as ThreadEvent
from threading import Thread

from .domain import DownloadStatus

# Rate-limit: não persistir progresso mais que uma vez por segundo por download_id
_LAST_PROGRESS_WRITE: dict[int, float] = {}
_MIN_PERSIST_INTERVAL = 1.0


def _resolve_torrent_input(magnet_or_url: str) -> tuple[str, str | None]:
    """Converte magnet ou URL de .torrent para o que o TorrentDownloader aceita.
    Retorna (path_ou_magnet, path_temp_para_apagar ou None).
    Se for URL http(s), baixa o .torrent para um arquivo temporário e retorna (path, path).
    """
    s = (magnet_or_url or "").strip()
    if not s:
        raise ValueError("Link vazio")
    if s.startswith("magnet:"):
        return s, None
    if s.startswith(("http://", "https://")):
        req = urllib.request.Request(s, headers={"User-Agent": "dl-torrent/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        fd, path = tempfile.mkstemp(suffix=".torrent")
        try:
            os.write(fd, data)
            os.close(fd)
            return path, path
        except Exception:
            os.close(fd)
            try:
                os.unlink(path)
            except OSError:
                pass
            raise
    # Path local
    return s, None


def _update_progress_from_status(download_id: int, status: object) -> None:
    """Escreve progresso no DB a partir do status do libtorrent.
    Não sobrescreve se o download já estiver marcado como completed (evita race com o worker).
    Rate-limit: não persiste mais que uma vez por segundo por download_id."""
    from .deps import get_repo

    try:
        now = time.monotonic()
        last = _LAST_PROGRESS_WRITE.get(download_id, 0.0)
        if now - last < _MIN_PERSIST_INTERVAL:
            return
        repo = get_repo()
        row = repo.get(download_id)
        if row and (row.get("status") or "").lower() == DownloadStatus.COMPLETED.value:
            return
        total_wanted = getattr(status, "total_wanted", 0) or 0
        total_done = getattr(status, "total_done", 0) or 0
        num_peers = getattr(status, "num_peers", 0) or 0
        num_seeds = getattr(status, "num_seeds", None)
        if num_seeds is None:
            num_seeds = getattr(status, "num_connections", None)  # fallback
        download_rate = getattr(status, "download_rate", 0) or 0

        progress = (100.0 * total_done / total_wanted) if total_wanted else 0.0
        eta_seconds: float | None = None
        if download_rate > 0 and total_wanted > total_done:
            eta_seconds = (total_wanted - total_done) / download_rate

        repo.update_progress(
            download_id,
            progress=progress,
            num_seeds=num_seeds if num_seeds is not None else None,
            num_peers=num_peers,
            download_speed_bps=download_rate,
            total_bytes=total_wanted,
            downloaded_bytes=total_done,
            eta_seconds=eta_seconds,
        )
        _LAST_PROGRESS_WRITE[download_id] = now
    except Exception:
        pass


def run_worker(download_id: int, stop_event: ThreadEvent | None = None) -> None:
    """Executa o download do registro `download_id` e atualiza o DB.
    Se stop_event for passado (modo thread), verifica periodicamente e para se stop_event.set() for chamado.
    """
    from .deps import get_repo

    repo = get_repo()
    row = repo.get(download_id)
    if not row:
        return
    if row["status"] not in (DownloadStatus.QUEUED.value, DownloadStatus.PAUSED.value):
        return

    magnet_or_url = row["magnet"]
    save_path = row["save_path"]

    repo.update_status(download_id, DownloadStatus.DOWNLOADING.value)
    if stop_event is None:
        repo.set_pid(download_id, os.getpid())
    else:
        repo.set_pid(download_id, None)

    os.environ["DL_TORRENT_DOWNLOAD_ID"] = str(download_id)

    temp_path_to_remove: str | None = None
    stopped_by_user = False
    completed_success = False
    try:
        torrent_input, temp_path_to_remove = _resolve_torrent_input(magnet_or_url)

        # Libtorrent direto (DHT, trackers, porta configuráveis). Sem fallback TorrentP.
        try:
            from .client.libtorrent_engine import run_download
        except ImportError as e:
            msg = (
                "libtorrent não disponível. Instale: pip install libtorrent (ou libtorrent-windows-dll no Windows). "
                "Diagnóstico: python scripts/debug_libtorrent.py."
            )
            repo.update_status(download_id, DownloadStatus.FAILED.value, error_message=msg)
            raise RuntimeError(msg) from e

        from .deps import get_settings
        port = 6881 + (download_id % 500)
        excluded = row.get("excluded_file_indices")
        if not isinstance(excluded, list):
            excluded = []
        interval = max(0.25, get_settings().download_progress_interval_seconds)

        def on_progress(st):
            _update_progress_from_status(download_id, st)

        success, torrent_name = run_download(
            torrent_input,
            save_path,
            port,
            progress_interval_seconds=interval,
            progress_callback=on_progress,
            stop_event=stop_event,
            excluded_file_indices=excluded,
        )
        if stop_event and stop_event.is_set():
            stopped_by_user = True
        elif success:
            completed_success = True
            repo.update_status(download_id, DownloadStatus.COMPLETED.value, progress=100.0)
            repo.update_progress(download_id, progress=100.0, eta_seconds=0.0)
            if torrent_name and str(torrent_name).strip():
                content_path = str(Path(save_path) / str(torrent_name).strip())
                repo.set_content_path(download_id, content_path)
        else:
            repo.update_status(download_id, DownloadStatus.FAILED.value, error_message="Download falhou ou timeout ao obter metadados.")

        if not stopped_by_user and completed_success:
            # Notificação: download concluído
            name = (row.get("name") or "").strip()
            try:
                from .db import notification_create
                notification_create(
                    "download_completed",
                    f"Download concluído: {(name or 'Item')[:80]}",
                    body=None,
                    payload={"download_id": download_id, "name": name},
                )
            except Exception:
                pass
            content_type = (row.get("content_type") or "music") if row.get("content_type") in ("music", "movies", "tv") else "music"
            if name:
                def _fetch_cover() -> None:
                    try:
                        from .web.cover_service import fetch_and_cache_cover
                        fetch_and_cache_cover(download_id, content_type, name)
                    except Exception:
                        pass
                t = Thread(target=_fetch_cover, daemon=True)
                t.start()
    except Exception as e:
        if stop_event and stop_event.is_set():
            stopped_by_user = True
        else:
            repo.update_status(download_id, DownloadStatus.FAILED.value, error_message=f"{type(e).__name__}: {e}")
            try:
                from .db import notification_create
                name = (row.get("name") or "").strip() if row else ""
                notification_create(
                    "download_failed",
                    f"Falha no download: {(name or str(download_id))[:60]}",
                    body=str(e)[:200],
                    payload={"download_id": download_id, "name": name},
                )
            except Exception:
                pass
    finally:
        repo.set_pid(download_id, None)
        os.environ.pop("DL_TORRENT_DOWNLOAD_ID", None)
        if (stop_event and stop_event.is_set()) or stopped_by_user:
            repo.update_status(download_id, DownloadStatus.PAUSED.value)
        if temp_path_to_remove and os.path.isfile(temp_path_to_remove):
            try:
                os.unlink(temp_path_to_remove)
            except OSError:
                pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python -m app.download_worker <download_id>")
    try:
        did = int(sys.argv[1])
    except ValueError:
        sys.exit("download_id deve ser um número")
    run_worker(did)
