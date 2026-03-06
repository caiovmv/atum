"""Testes dos repositórios (wishlist, download) com PostgreSQL. Exige DATABASE_URL."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.requires_db


@pytest.fixture(autouse=True)
def _require_database_url():
    if not (os.environ.get("DATABASE_URL") or "").strip():
        pytest.skip("DATABASE_URL não definido")


class TestWishlistRepository:
    """Testes da wishlist (PostgreSQL)."""

    def test_add_list_delete(self) -> None:
        from app.db import (
            wishlist_add_term,
            wishlist_delete_by_id,
            wishlist_list_all,
        )
        id1 = wishlist_add_term("Artist - Album")
        id2 = wishlist_add_term("Other Term")
        assert id1 >= 1
        assert id2 >= 1
        all_ = wishlist_list_all()
        assert len(all_) >= 2
        terms = [r["term"] for r in all_ if r["id"] in (id1, id2)]
        assert "Artist - Album" in terms
        assert "Other Term" in terms
        assert wishlist_delete_by_id(id1) is True
        assert wishlist_delete_by_id(id1) is False
        wishlist_delete_by_id(id2)

    def test_add_empty_returns_zero(self) -> None:
        from app.db import wishlist_add_term
        assert wishlist_add_term("") == 0

    def test_get_by_id(self) -> None:
        from app.db import wishlist_add_term, wishlist_get_by_id, wishlist_delete_by_id
        wid = wishlist_add_term("Test Term")
        row = wishlist_get_by_id(wid)
        assert row is not None
        assert row["term"] == "Test Term"
        assert wishlist_get_by_id(99999) is None
        wishlist_delete_by_id(wid)


class TestDownloadRepository:
    """Testes do repositório de downloads (PostgreSQL)."""

    def test_add_list_get_update_delete(self) -> None:
        from app.deps import get_repo
        from app.domain import DownloadStatus
        repo = get_repo()
        did = repo.add("magnet:?xt=urn:btih:abc", "/tmp/save", "My Torrent")
        assert did >= 1
        rows = repo.list()
        assert len(rows) >= 1
        row = next((r for r in rows if r["id"] == did), None)
        assert row is not None
        assert row["magnet"] == "magnet:?xt=urn:btih:abc"
        assert row["name"] == "My Torrent"
        assert row["status"] == "queued"
        one = repo.get(did)
        assert one is not None
        assert one["status"] == "queued"
        repo.update_status(did, DownloadStatus.DOWNLOADING.value)
        one = repo.get(did)
        assert one is not None
        assert one["status"] == "downloading"
        repo.delete(did)
        assert repo.get(did) is None

    def test_list_filter_by_status(self) -> None:
        from app.deps import get_repo
        from app.domain import DownloadStatus
        repo = get_repo()
        id1 = repo.add("magnet:1", "/tmp", None)
        id2 = repo.add("magnet:2", "/tmp", None)
        repo.update_status(id2, DownloadStatus.COMPLETED.value)
        queued = repo.list(status_filter="queued")
        completed = repo.list(status_filter="completed")
        assert any(r["id"] == id1 for r in queued)
        assert any(r["id"] == id2 for r in completed)
        repo.delete(id1)
        repo.delete(id2)
