"""Gerenciador de downloads em background: adicionar, listar, iniciar, parar, deletar. Usa threads (sem abrir novos terminais)."""

from __future__ import annotations

import logging
import os
import signal
import threading
from pathlib import Path

from .domain import DownloadStatus
from .deps import get_repo, set_overrides, clear_overrides

logger = logging.getLogger(__name__)


def _publish_download_event(event_type: str, download_id: int | None = None) -> None:
    """Publica evento no Redis Pub/Sub para o SSE de downloads reagir."""
    try:
        from .event_bus import CHANNEL_DOWNLOADS, publish
        payload: dict = {"type": event_type}
        if download_id is not None:
            payload["id"] = download_id
        publish(CHANNEL_DOWNLOADS, payload)
    except Exception:
        pass


# Re-export para testes
def set_download_repository(repo) -> None:
    """Injeta o repositório (para testes). None restaura o padrão."""
    set_overrides(repo=repo)


# Registro de workers em thread (download_id -> thread e event para stop)
_worker_threads: dict[int, threading.Thread] = {}
_worker_stop_events: dict[int, threading.Event] = {}
_lock = threading.Lock()


def is_process_alive(pid: int | None) -> bool:
    """Retorna True se o processo com o PID ainda está em execução."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, OSError):
        return False


def get_worker_alive(row: dict) -> bool | None:
    """Retorna True/False se o worker (processo ou thread) está vivo; None se não aplicável."""
    if (row.get("status") or "").lower() != DownloadStatus.DOWNLOADING.value:
        return None
    pid = row.get("pid")
    if pid is not None:
        return is_process_alive(pid)
    did = row.get("id")
    with _lock:
        t = _worker_threads.get(did)
    return t.is_alive() if t else False


def restart_dead_workers() -> int:
    """Reinicia downloads em status 'downloading' cujo processo ou thread está morto. Retorna quantos foram reiniciados."""
    repo = get_repo()
    rows = repo.list(status_filter=DownloadStatus.DOWNLOADING.value)
    restarted = 0
    for r in rows:
        did = r["id"]
        pid = r.get("pid")
        is_dead = False
        if pid is not None:
            is_dead = not is_process_alive(pid)
        else:
            with _lock:
                t = _worker_threads.get(did)
            is_dead = t is None or not t.is_alive()
        if not is_dead:
            continue
        repo.update_status(did, DownloadStatus.QUEUED.value)
        repo.set_pid(did, None)
        if start(did):
            restarted += 1
    return restarted


def add(
    magnet: str,
    save_path: str,
    name: str | None = None,
    content_type: str | None = None,
    excluded_file_indices: list[int] | None = None,
    torrent_files: list[dict] | None = None,
    torrent_url: str | None = None,
) -> int:
    """Adiciona um download à fila. content_type opcional: music, movies, tv. excluded_file_indices: índices a não baixar. torrent_files: lista opcional [{index, path, size}] para listagem consistente. Retorna o id."""
    save_path = str(Path(save_path).expanduser().resolve())
    Path(save_path).mkdir(parents=True, exist_ok=True)
    did = get_repo().add(magnet, save_path, name, content_type=content_type, excluded_file_indices=excluded_file_indices, torrent_url=torrent_url)
    if did and torrent_files:
        get_repo().set_torrent_files(did, torrent_files)
    if did:
        _publish_download_event("added", did)
    return did


def list_downloads(status_filter: str | None = None) -> list[dict]:
    """Lista downloads (opcionalmente filtrado por status)."""
    return get_repo().list(status_filter=status_filter)


def _sanitize_for_path(name: str) -> str:
    """Nome seguro para usar como pasta (remove caracteres inválidos no filesystem)."""
    import re
    s = (name or "").strip()
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    return s.strip() or "unknown"


def reconcile_downloads_with_filesystem() -> int:
    """Remove do DB registros completed cujo content_path não existe mais no disco; evict capa (Redis + arquivos).
    Para registros que permanecem, limpa cover_path no DB e evict se arquivo de capa não existir.
    Retorna quantos foram removidos."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        from .web.cover_service import evict_cover_for_download
    except Exception:
        evict_cover_for_download = None
    repo = get_repo()
    rows = repo.list(status_filter=DownloadStatus.COMPLETED.value)
    logger.info(f"  [reconcile] Verificando %d download(s) completed.", len(rows))

    # Phase 1: check Path.exists() in parallel for all rows
    def _resolve_row(r: dict) -> tuple[dict, str, bool]:
        """Returns (row, resolved_content_path, exists)."""
        content_path = (r.get("content_path") or "").strip()
        if not content_path:
            save_path = (r.get("save_path") or "").strip()
            name = (r.get("name") or "").strip()
            if save_path and name:
                inferred = Path(save_path) / _sanitize_for_path(name)
                if inferred.exists():
                    return (r, str(inferred), True)
                return (r, "", False)
            return (r, "", False)
        return (r, content_path, Path(content_path).exists())

    resolved: list[tuple[dict, str, bool]] = []
    if rows:
        max_w = min(len(rows), 8)
        with ThreadPoolExecutor(max_workers=max_w) as pool:
            resolved = list(pool.map(_resolve_row, rows))

    removed = 0
    for r, content_path, exists in resolved:
        did = r["id"]
        orig_cp = (r.get("content_path") or "").strip()
        if not orig_cp and not content_path:
            continue
        if not orig_cp and content_path and exists:
            repo.set_content_path(did, content_path)
            continue
        if not exists:
            if not orig_cp:
                logger.info("  [reconcile] Removendo download id=%s (sem content_path, path inferido não existe).", did)
            else:
                logger.info("  [reconcile] Removendo download id=%s (path não existe): %s", did, orig_cp)
            if evict_cover_for_download:
                try:
                    evict_cover_for_download(did)
                except Exception as exc:
                    logger.debug("Falha ao evictar capa do download %s: %s", did, exc)
            if repo.delete(did):
                removed += 1

    # Phase 2: clean stale cover paths (parallel existence check)
    remaining = repo.list(status_filter=DownloadStatus.COMPLETED.value)
    cover_checks: list[tuple[dict, bool, bool]] = []

    def _check_covers(r: dict) -> tuple[dict, bool, bool]:
        small = (r.get("cover_path_small") or "").strip()
        large = (r.get("cover_path_large") or "").strip()
        small_ok = not small or Path(small).exists()
        large_ok = not large or Path(large).exists()
        return (r, small_ok, large_ok)

    if remaining:
        with_covers = [r for r in remaining if (r.get("cover_path_small") or "").strip() or (r.get("cover_path_large") or "").strip()]
        if with_covers:
            max_w = min(len(with_covers), 8)
            with ThreadPoolExecutor(max_workers=max_w) as pool:
                cover_checks = list(pool.map(_check_covers, with_covers))

    for r, small_ok, large_ok in cover_checks:
        if not small_ok or not large_ok:
            did = r["id"]
            repo.set_cover_paths(did, cover_path_small=None, cover_path_large=None)
            if evict_cover_for_download:
                try:
                    evict_cover_for_download(did)
                except Exception as exc:
                    logger.debug("Falha ao evictar capa do download %s: %s", did, exc)
    return removed


def _run_worker_thread(download_id: int, stop_event: threading.Event) -> None:
    """Wrapper que chama run_worker e ao terminar remove do registro."""
    from . import download_worker

    try:
        download_worker.run_worker(download_id, stop_event=stop_event)
    finally:
        with _lock:
            _worker_threads.pop(download_id, None)
            _worker_stop_events.pop(download_id, None)
        _publish_download_event("finished", download_id)


def start(download_id: int) -> bool:
    """Inicia o download em background (thread no mesmo processo). Retorna True se enfileirou/iniciou."""
    row = get_repo().get(download_id)
    if not row:
        return False
    if row["status"] not in (DownloadStatus.QUEUED.value, DownloadStatus.PAUSED.value):
        return False

    with _lock:
        if download_id in _worker_threads and _worker_threads[download_id].is_alive():
            return True
        stop_event = threading.Event()
        _worker_stop_events[download_id] = stop_event
        t = threading.Thread(
            target=_run_worker_thread,
            args=(download_id, stop_event),
            daemon=True,
            name=f"download-{download_id}",
        )
        _worker_threads[download_id] = t
        try:
            t.start()
        except Exception:
            _worker_threads.pop(download_id, None)
            _worker_stop_events.pop(download_id, None)
            return False
    _publish_download_event("started", download_id)
    return True


def retry(download_id: int) -> bool:
    """Re-tenta um download falhado: reseta status para queued e inicia novamente.
    Retorna True se enfileirou com sucesso."""
    repo = get_repo()
    row = repo.get(download_id)
    if not row:
        return False
    if row["status"] != DownloadStatus.FAILED.value:
        return False
    repo.update_status(download_id, DownloadStatus.QUEUED.value, error_message=None, progress=0.0)
    repo.set_pid(download_id, None)
    _publish_download_event("retried", download_id)
    return start(download_id)


def stop(download_id: int) -> bool:
    """Para o download (sinaliza a thread ou mata o processo). Retorna True se parou ou já estava parado."""
    row = get_repo().get(download_id)
    if not row:
        return False
    pid = row.get("pid")
    if not pid:
        if row["status"] in (
            DownloadStatus.QUEUED.value,
            DownloadStatus.PAUSED.value,
            DownloadStatus.COMPLETED.value,
            DownloadStatus.FAILED.value,
        ):
            return True
        # Worker em thread: sinalizar parada
        with _lock:
            ev = _worker_stop_events.get(download_id)
        if ev:
            ev.set()
        get_repo().update_status(download_id, DownloadStatus.PAUSED.value)
        get_repo().set_pid(download_id, None)
        _publish_download_event("stopped", download_id)
        return True

    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass
    get_repo().update_status(download_id, DownloadStatus.PAUSED.value)
    get_repo().set_pid(download_id, None)
    _publish_download_event("stopped", download_id)
    return True


def delete(download_id: int, remove_files: bool = False) -> bool:
    """Remove o download da lista. Evict capa (Redis + arquivos). Se remove_files=True, apaga a pasta do torrent."""
    row = get_repo().get(download_id)
    if not row:
        return False
    pid = row.get("pid")
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
    else:
        with _lock:
            ev = _worker_stop_events.get(download_id)
        if ev:
            ev.set()
    ok = get_repo().delete(download_id)
    if ok:
        try:
            from .web.cover_service import evict_cover_for_download
            evict_cover_for_download(download_id)
        except Exception as exc:
            logger.debug("Falha ao evictar capa do download %s: %s", download_id, exc)
        if remove_files and row.get("save_path"):
            import shutil
            p = Path(row["save_path"])
            if p.is_dir():
                try:
                    shutil.rmtree(p, ignore_errors=True)
                except Exception as exc:
                    logger.debug("Falha ao remover arquivos do download %s: %s", download_id, exc)
        _publish_download_event("deleted", download_id)
    return ok
