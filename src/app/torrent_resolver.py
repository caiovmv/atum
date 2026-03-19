"""Resolução centralizada de torrent input (torrent_url vs magnet) com fallback.

Usado pelo download_worker e pelo endpoint de metadados para garantir
comportamento consistente e resiliência em ambientes Docker.
"""

from __future__ import annotations

import logging
import os
import tempfile
import urllib.request

logger = logging.getLogger(__name__)


def resolve_torrent_input(
    magnet: str | None = None,
    torrent_url: str | None = None,
) -> tuple[str, str | None]:
    """Resolve o input para libtorrent com fallback automático.

    Estratégia:
      1. ``torrent_url`` (HTTP) – baixa o .torrent para arquivo temporário.
         Funciona em Docker sem depender de DHT.
      2. ``magnet`` – retorna a string magnet diretamente (requer DHT/trackers).

    Returns:
        (input_para_libtorrent, path_temporário_para_apagar | None)

    Raises:
        ValueError: nenhum input disponível ou ambos falharam.
    """
    magnet_clean = (magnet or "").strip() or None
    url_clean = (torrent_url or "").strip() or None

    if not magnet_clean and not url_clean:
        logger.error("Nenhum input disponível (magnet=None, torrent_url=None)")
        raise ValueError("Nem magnet nem torrent_url foram fornecidos")

    # 1. Tentar torrent_url (preferido – não depende de DHT)
    if url_clean and url_clean.startswith(("http://", "https://")):
        try:
            logger.info("Tentando torrent_url: %s", url_clean[:120])
            path = _download_torrent_file(url_clean)
            logger.info("torrent_url resolvido com sucesso -> %s", path)
            return path, path
        except Exception as exc:
            if magnet_clean:
                logger.warning(
                    "torrent_url falhou (%s), fallback para magnet", exc
                )
            else:
                logger.error("torrent_url falhou e magnet não disponível: %s", exc)
                raise ValueError(
                    f"torrent_url falhou e magnet não disponível: {exc}"
                ) from exc

    # 2. Fallback: magnet
    if magnet_clean:
        if magnet_clean.startswith("magnet:"):
            info_hash = _extract_info_hash(magnet_clean)
            logger.info("Usando magnet link (info_hash=%s)", info_hash)
            return magnet_clean, None
        # Pode ser um path local de .torrent
        logger.info("Usando path local: %s", magnet_clean[:120])
        return magnet_clean, None

    raise ValueError("Nenhum input válido disponível")


def _download_torrent_file(url: str, timeout: int = 60) -> str:
    """Baixa um .torrent via HTTP e salva em arquivo temporário. Retorna o path."""
    req = urllib.request.Request(url, headers={"User-Agent": "dl-torrent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    if not data:
        raise ValueError("Resposta vazia ao baixar .torrent")
    fd, path = tempfile.mkstemp(suffix=".torrent")
    try:
        os.write(fd, data)
        os.close(fd)
        return path
    except Exception:
        os.close(fd)
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def _extract_info_hash(magnet: str) -> str:
    """Extrai o info_hash curto de um magnet link para logging."""
    import re
    match = re.search(r"btih:([A-Fa-f0-9]{40}|[A-Za-z2-7]{32})", magnet)
    if match:
        return match.group(1)[:12] + "..."
    return "unknown"


def cleanup_temp_file(path: str | None) -> None:
    """Remove arquivo temporário se existir. Seguro para chamar com None."""
    if path and os.path.isfile(path):
        try:
            os.unlink(path)
        except OSError:
            pass
