"""Testes do domínio (download status, etc.)."""

from __future__ import annotations

import pytest

from app.domain.download_status import DownloadStatus


def test_download_status_values() -> None:
    assert DownloadStatus.QUEUED.value == "queued"
    assert DownloadStatus.DOWNLOADING.value == "downloading"
    assert DownloadStatus.COMPLETED.value == "completed"
    assert DownloadStatus.FAILED.value == "failed"
    assert DownloadStatus.PAUSED.value == "paused"


def test_download_status_string_enum() -> None:
    assert str(DownloadStatus.QUEUED) == "DownloadStatus.QUEUED"
    assert DownloadStatus.QUEUED.value == "queued"
