"""Motor de download usando libtorrent diretamente: sessão com DHT, trackers e porta configuráveis."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

PUBLIC_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.tiny-vps.com:6969/announce",
    "udp://exodus.desync.com:6969/announce",
]

DHT_ROUTERS = [
    ("router.bittorrent.com", 6881),
    ("router.utorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
]


def _create_session(port: int):
    """Cria sessão libtorrent com DHT, LSD e listen na porta."""
    import libtorrent as lt
    settings = {"listen_interfaces": f"0.0.0.0:{port}"}
    try:
        ses = lt.session(settings)
    except TypeError:
        ses = lt.session()
        ses.listen_on(port, port)
    for router, rport in DHT_ROUTERS:
        try:
            ses.add_dht_router(router, rport)
        except Exception:
            pass
    ses.start_dht()
    try:
        ses.start_lsd()
    except Exception:
        pass
    logger.debug("Sessão libtorrent criada na porta %d", port)
    return ses


def _add_torrent_to_session(ses, magnet_or_path: str, save_path: str):
    """Adiciona torrent à sessão (magnet ou path .torrent). Retorna (handle, is_magnet)."""
    import libtorrent as lt
    save_path = str(Path(save_path).expanduser().resolve())
    if magnet_or_path.strip().startswith("magnet:"):
        atp = lt.parse_magnet_uri(magnet_or_path.strip())
        atp.save_path = save_path
        try:
            atp.storage_mode = lt.storage_mode_t(2)
        except (TypeError, AttributeError):
            pass
        existing = getattr(atp, "trackers", None) or []
        atp.trackers = list(existing) + PUBLIC_TRACKERS
        handle = ses.add_torrent(atp)
        logger.info("Torrent adicionado via magnet (aguardando metadados via DHT/trackers)")
        return handle, True
    # Arquivo .torrent
    logger.info("Torrent adicionado via arquivo .torrent: %s", magnet_or_path[:80])
    ti = lt.torrent_info(magnet_or_path.strip())
    try:
        atp = lt.add_torrent_params()
        atp.ti = ti
        atp.save_path = save_path
        try:
            atp.storage_mode = lt.storage_mode_t(2)
        except (TypeError, AttributeError):
            pass
        atp.trackers = list(PUBLIC_TRACKERS)
        handle = ses.add_torrent(atp)
    except (TypeError, AttributeError):
        handle = ses.add_torrent({"ti": ti, "save_path": save_path})
    return handle, False


def run_download(
    magnet_or_path: str,
    save_path: str,
    port: int,
    *,
    progress_interval_seconds: float = 1.0,
    progress_callback: Callable[[object], None] | None = None,
    stop_event: object | None = None,
    excluded_file_indices: list[int] | None = None,
) -> tuple[bool, str | None]:
    """
    Executa um download com libtorrent (sessão com DHT, LSD, trackers).

    Retorna (success, torrent_name).
    torrent_name é o nome do torrent (pasta/arquivo) para content_path; None se falhou ou parado.
    """
    import libtorrent as lt

    ses = _create_session(port)
    try:
        handle, is_magnet = _add_torrent_to_session(ses, magnet_or_path, save_path)
        if is_magnet:
            metadata_timeout = 300
            deadline = time.monotonic() + metadata_timeout
            logger.info("Aguardando metadados via DHT (timeout=%ds)...", metadata_timeout)
            while not handle.has_metadata():
                if stop_event is not None and getattr(stop_event, "is_set", lambda: False)():
                    logger.info("Metadata wait cancelado pelo usuário")
                    try:
                        ses.remove_torrent(handle)
                    except Exception:
                        pass
                    return False, None
                elapsed = time.monotonic() - (deadline - metadata_timeout)
                if time.monotonic() > deadline:
                    logger.warning(
                        "Timeout ao obter metadados via DHT após %.0fs",
                        elapsed,
                    )
                    try:
                        ses.remove_torrent(handle)
                    except Exception:
                        pass
                    return False, None
                time.sleep(0.5)
            logger.info("Metadados obtidos com sucesso via DHT")

        if excluded_file_indices:
            for idx in excluded_file_indices:
                try:
                    handle.set_file_priority(int(idx), 0)
                except Exception:
                    pass

        interval = max(0.25, progress_interval_seconds)
        while True:
            if stop_event is not None and getattr(stop_event, "is_set", lambda: False)():
                logger.info("Download cancelado pelo usuário")
                try:
                    ses.remove_torrent(handle)
                except Exception:
                    pass
                return False, None
            st = handle.status()
            if progress_callback:
                progress_callback(st)
            if st.is_seeding:
                break
            errc = getattr(st, "errc", None)
            if errc is not None:
                err_val = getattr(errc, "value", lambda: 0)()
                if err_val != 0:
                    err_msg = getattr(errc, "message", lambda: str(errc))()
                    logger.error("Erro fatal do libtorrent (code=%d): %s", err_val, err_msg)
                    try:
                        ses.remove_torrent(handle)
                    except Exception:
                        pass
                    return False, None
            time.sleep(interval)

        name = None
        try:
            ti = handle.get_torrent_info()
            if ti:
                n = ti.name()
                name = n.decode("utf-8", errors="replace") if isinstance(n, bytes) else str(n or "")
        except Exception:
            pass
        try:
            ses.remove_torrent(handle)
        except Exception:
            pass
        logger.info("Download concluído: %s", name or "(sem nome)")
        return True, (name or "").strip() or None
    finally:
        try:
            ses.pause()
            del ses
        except Exception:
            pass
