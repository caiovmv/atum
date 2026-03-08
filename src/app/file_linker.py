"""Utilitário para operações de arquivo na organização da biblioteca: rename, hardlink, copy."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_parent(path: Path) -> None:
    """Cria diretórios intermediários se necessário."""
    path.parent.mkdir(parents=True, exist_ok=True)


def rename_file(src: Path, dst: Path) -> bool:
    """Renomeia/move arquivo (mesmo filesystem). Atômico quando possível."""
    if src == dst:
        return True
    if not src.exists():
        logger.warning("rename_file: origem não existe: %s", src)
        return False
    if dst.exists():
        if _same_file(src, dst):
            logger.debug("rename: destino já é o mesmo arquivo: %s", dst)
            return True
        logger.warning("rename_file: destino já existe (diferente): %s", dst)
        return False
    ensure_parent(dst)
    try:
        src.rename(dst)
        logger.info("rename: %s -> %s", src, dst)
        return True
    except OSError as e:
        logger.error("rename falhou: %s -> %s: %s", src, dst, e)
        return False


def hardlink_file(src: Path, dst: Path) -> bool:
    """Cria hardlink. Fallback para copy se cross-device."""
    if src == dst:
        return True
    if not src.is_file():
        logger.warning("hardlink: origem não é arquivo: %s", src)
        return False
    ensure_parent(dst)
    if dst.exists():
        if _same_file(src, dst):
            logger.debug("hardlink: destino já é o mesmo arquivo: %s", dst)
            return True
        logger.warning("hardlink: destino já existe (diferente): %s", dst)
        return False
    try:
        os.link(str(src), str(dst))
        logger.info("hardlink: %s -> %s", src, dst)
        return True
    except OSError:
        logger.info("hardlink cross-device; fazendo copy: %s -> %s", src, dst)
        return copy_file(src, dst)


def copy_file(src: Path, dst: Path) -> bool:
    """Copia arquivo preservando metadados."""
    if src == dst:
        return True
    if not src.is_file():
        logger.warning("copy: origem não é arquivo: %s", src)
        return False
    ensure_parent(dst)
    try:
        shutil.copy2(str(src), str(dst))
        logger.info("copy: %s -> %s", src, dst)
        return True
    except OSError as e:
        logger.error("copy falhou: %s -> %s: %s", src, dst, e)
        return False


def _same_file(a: Path, b: Path) -> bool:
    """Verifica se dois paths apontam para o mesmo inode (hardlink)."""
    try:
        return os.path.samefile(str(a), str(b))
    except OSError:
        return False


def link_or_copy(src: Path, dst: Path, mode: str = "hardlink_to_library") -> bool:
    """
    Executa a operação conforme o modo:
    - 'in_place': rename (move)
    - 'hardlink_to_library': hardlink com fallback copy
    - 'copy_to_library': copy
    """
    if mode == "in_place":
        return rename_file(src, dst)
    if mode == "hardlink_to_library":
        return hardlink_file(src, dst)
    if mode == "copy_to_library":
        return copy_file(src, dst)
    logger.warning("Modo desconhecido '%s'; usando rename.", mode)
    return rename_file(src, dst)


def rename_directory(src: Path, dst: Path) -> bool:
    """Renomeia diretório inteiro. Para in-place reorganization."""
    if src == dst:
        return True
    if not src.is_dir():
        logger.warning("rename_dir: origem não é diretório: %s", src)
        return False
    ensure_parent(dst)
    try:
        src.rename(dst)
        logger.info("rename_dir: %s -> %s", src, dst)
        return True
    except OSError as e:
        logger.error("rename_dir falhou: %s -> %s: %s", src, dst, e)
        return False


def cleanup_empty_dirs(path: Path, stop_at: Path | None = None) -> None:
    """Remove diretórios vazios subindo até stop_at (ou raiz do path)."""
    current = path
    while current != stop_at and current.parent != current:
        if current.is_dir() and not any(current.iterdir()):
            try:
                current.rmdir()
                logger.debug("Removido diretório vazio: %s", current)
            except OSError:
                break
        else:
            break
        current = current.parent
