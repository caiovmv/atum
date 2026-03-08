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
) -> int:
    """Adiciona um download à fila. content_type opcional: music, movies, tv. excluded_file_indices: índices a não baixar. torrent_files: lista opcional [{index, path, size}] para listagem consistente. Retorna o id."""
    save_path = str(Path(save_path).expanduser().resolve())
    Path(save_path).mkdir(parents=True, exist_ok=True)
    did = get_repo().add(magnet, save_path, name, content_type=content_type, excluded_file_indices=excluded_file_indices)
    if did and torrent_files:
        get_repo().set_torrent_files(did, torrent_files)
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
    try:
        from .web.cover_service import evict_cover_for_download
    except Exception:
        evict_cover_for_download = None
    repo = get_repo()
    rows = repo.list(status_filter=DownloadStatus.COMPLETED.value)
    logger.info(f"  [reconcile] Verificando %d download(s) completed.", len(rows))
    removed = 0
    for r in rows:
        did = r["id"]
        content_path = (r.get("content_path") or "").strip()
        if not content_path:
            save_path = (r.get("save_path") or "").strip()
            name = (r.get("name") or "").strip()
            if save_path and name:
                inferred = Path(save_path) / _sanitize_for_path(name)
                if inferred.exists():
                    repo.set_content_path(did, str(inferred))
                    content_path = str(inferred)
                else:
                    if evict_cover_for_download:
                        try:
                            evict_cover_for_download(did)
                        except Exception as exc:
                            logger.debug("Falha ao evictar capa do download %s: %s", did, exc)
                    if repo.delete(did):
                        removed += 1
                        logger.info("  [reconcile] Removendo download id=%s (sem content_path, path inferido não existe).", did)
                    continue
            else:
                continue
        if not Path(content_path).exists():
            logger.info("  [reconcile] Removendo download id=%s (path não existe): %s", did, content_path)
            if evict_cover_for_download:
                try:
                    evict_cover_for_download(did)
                except Exception as exc:
                    logger.debug("Falha ao evictar capa do download %s: %s", did, exc)
            if repo.delete(did):
                removed += 1
    # Limpar cover_path e evict quando arquivo de capa não existe
    for r in repo.list(status_filter=DownloadStatus.COMPLETED.value):
        did = r["id"]
        small = (r.get("cover_path_small") or "").strip()
        large = (r.get("cover_path_large") or "").strip()
        if not small and not large:
            continue
        need_clear = False
        if small and not Path(small).exists():
            need_clear = True
        if large and not Path(large).exists():
            need_clear = True
        if need_clear:
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
    return True


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
        return True

    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass
    get_repo().update_status(download_id, DownloadStatus.PAUSED.value)
    get_repo().set_pid(download_id, None)
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
    return ok
