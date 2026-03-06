"""Obtém metadados (nome + lista de arquivos) de magnet ou arquivo .torrent (URL/bytes)."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path


def _torrent_info_to_metadata(ti) -> dict:
    """Extrai name e files de um objeto libtorrent torrent_info. Formato: { name, files }."""
    name = ti.name() or ""
    name_str = name.decode("utf-8", errors="replace") if isinstance(name, bytes) else str(name or "")
    files = []
    num_files = ti.num_files()
    file_storage = ti.files()
    for i in range(num_files):
        path = file_storage.file_path(i)
        size = file_storage.file_size(i)
        path_str = path.decode("utf-8", errors="replace") if isinstance(path, bytes) else str(path)
        files.append({"index": int(i), "path": path_str, "size": int(size)})
    return {"name": name_str, "files": files}


def parse_torrent_bytes(data: bytes) -> dict | None:
    """
    Parseia um arquivo .torrent (bytes) e retorna { name, files }.
    Não usa rede; ideal quando já se tem o .torrent.
    """
    if not data:
        return None
    try:
        import libtorrent as lt
    except ImportError:
        return None
    try:
        ti = lt.torrent_info(data)
        return _torrent_info_to_metadata(ti)
    except Exception:
        return None


def fetch_metadata_from_torrent_url(url: str, timeout_seconds: int = 30) -> dict | None:
    """
    Baixa o .torrent da URL, parseia e retorna { name, files }. Remove o arquivo temporário depois.
    Não usa DHT; funciona bem em Docker e ambientes restritos.
    """
    url = (url or "").strip()
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "dl-torrent/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            data = resp.read()
    except Exception:
        return None
    return parse_torrent_bytes(data)


def fetch_torrent_metadata(magnet: str, timeout_seconds: int = 90) -> dict | None:
    """
    Conecta aos peers, obtém apenas os metadados do torrent e retorna nome e lista de arquivos.
    Retorna None se timeout ou libtorrent indisponível.
    Em Docker a resolução pode falhar se DHT/peers não forem acessíveis; aumentar timeout ajuda.
    """
    magnet = (magnet or "").strip()
    if not magnet or not magnet.startswith("magnet:"):
        return None
    try:
        import libtorrent as lt
    except ImportError:
        return None

    save_path = tempfile.mkdtemp(prefix="dl_torrent_meta_")
    try:
        ses = lt.session()
        # Bootstrap DHT para melhor descoberta de peers a partir de magnet
        for router, port in [("router.bittorrent.com", 6881), ("router.utorrent.com", 6881), ("dht.transmissionbt.com", 6881)]:
            try:
                ses.add_dht_router(router, port)
            except Exception:
                pass
        ses.start_dht()
        try:
            ses.start_lsd()
        except Exception:
            pass
        # Usar add_torrent_params com trackers públicos (DHT costuma falhar em Docker)
        _public_trackers = [
            "udp://tracker.opentrackr.org:1337/announce",
            "udp://open.stealth.si:80/announce",
            "udp://tracker.torrent.eu.org:451/announce",
            "udp://tracker.tiny-vps.com:6969/announce",
            "udp://exodus.desync.com:6969/announce",
        ]
        try:
            atp = lt.parse_magnet_uri(magnet)
            atp.save_path = save_path
            atp.storage_mode = lt.storage_mode_t(2)
            existing = getattr(atp, "trackers", None) or []
            atp.trackers = list(existing) + _public_trackers
            handle = ses.add_torrent(atp)
        except (AttributeError, TypeError):
            params = {
                "save_path": save_path,
                "storage_mode": lt.storage_mode_t(2),
                "paused": True,
                "auto_managed": False,
                "duplicate_is_error": False,
            }
            handle = lt.add_magnet_uri(ses, magnet, params)
        deadline = time.monotonic() + timeout_seconds
        while not handle.has_metadata():
            if time.monotonic() > deadline:
                try:
                    ses.remove_torrent(handle)
                except Exception:
                    pass
                return None
            time.sleep(0.5)

        ti = handle.get_torrent_info()
        try:
            ses.remove_torrent(handle)
        except Exception:
            pass
        return _torrent_info_to_metadata(ti)
    except Exception:
        return None
    finally:
        try:
            import shutil
            shutil.rmtree(save_path, ignore_errors=True)
        except Exception:
            pass
