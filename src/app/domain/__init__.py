"""Domínio: entidades, value objects e portas (abstrações)."""

from .download_status import DownloadStatus
from .ports import DownloadRepository

__all__ = ["DownloadStatus", "DownloadRepository"]
