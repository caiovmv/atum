"""Testes dos repositórios (histórico, wishlist, download) com DB temporário."""

from __future__ import annotations

import pytest

from app.db import (
    history_add_query,
    history_get_by_id,
    history_list_recent,
    history_prune,
    wishlist_add_term,
    wishlist_delete_by_id,
    wishlist_get_by_id,
    wishlist_list_all,
)
from app.repositories.download_repository import (
    download_add,
    download_delete,
    download_get,
    download_list,
    download_update_status,
)


class TestSearchHistoryRepository:
    """Testes do histórico de buscas."""

    def test_add_and_list(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        id1 = history_add_query("Pink Floyd The Wall", db_path=p)
        id2 = history_add_query("Arctic Monkeys AM", db_path=p)
        assert id1 >= 1
        assert id2 >= 1
        assert id2 != id1
        recent = history_list_recent(limit=10, db_path=p)
        assert len(recent) == 2
        queries = {r["query"] for r in recent}
        assert queries == {"Pink Floyd The Wall", "Arctic Monkeys AM"}

    def test_add_empty_returns_zero(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        assert history_add_query("", db_path=p) == 0
        assert history_add_query("   ", db_path=p) == 0

    def test_get_by_id(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        history_add_query("Test Query", db_path=p)
        recent = history_list_recent(limit=1, db_path=p)
        hid = recent[0]["id"]
        row = history_get_by_id(hid, db_path=p)
        assert row is not None
        assert row["query"] == "Test Query"

    def test_get_by_id_missing(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        assert history_get_by_id(99999, db_path=p) is None

    def test_prune(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        for i in range(5):
            history_add_query(f"query {i}", db_path=p)
        removed = history_prune(max_entries=2, db_path=p)
        assert removed == 3
        recent = history_list_recent(limit=10, db_path=p)
        assert len(recent) == 2


class TestWishlistRepository:
    """Testes da wishlist."""

    def test_add_list_delete(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        id1 = wishlist_add_term("Artist - Album", db_path=p)
        id2 = wishlist_add_term("Other Term", db_path=p)
        assert id1 >= 1
        assert id2 >= 1
        all_ = wishlist_list_all(db_path=p)
        assert len(all_) == 2
        assert all_[0]["term"] == "Artist - Album"
        assert wishlist_delete_by_id(id1, db_path=p) is True
        assert wishlist_list_all(db_path=p) == [all_[1]]
        assert wishlist_delete_by_id(id1, db_path=p) is False

    def test_add_empty_returns_zero(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        assert wishlist_add_term("", db_path=p) == 0

    def test_get_by_id(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        wid = wishlist_add_term("Test Term", db_path=p)
        row = wishlist_get_by_id(wid, db_path=p)
        assert row is not None
        assert row["term"] == "Test Term"
        assert wishlist_get_by_id(99999, db_path=p) is None


class TestDownloadRepository:
    """Testes do repositório de downloads."""

    def test_add_list_get_update_delete(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        did = download_add("magnet:?xt=urn:btih:abc", "/tmp/save", "My Torrent", db_path=p)
        assert did >= 1
        rows = download_list(db_path=p)
        assert len(rows) == 1
        assert rows[0]["magnet"] == "magnet:?xt=urn:btih:abc"
        assert rows[0]["name"] == "My Torrent"
        assert rows[0]["status"] == "queued"
        one = download_get(did, db_path=p)
        assert one is not None
        assert one["status"] == "queued"
        download_update_status(did, "downloading", db_path=p)
        one = download_get(did, db_path=p)
        assert one["status"] == "downloading"
        download_delete(did, db_path=p)
        assert download_get(did, db_path=p) is None

    def test_list_filter_by_status(self, db_path: pytest.Path) -> None:
        from pathlib import Path
        p = Path(str(db_path))
        download_add("magnet:1", "/tmp", None, db_path=p)
        download_add("magnet:2", "/tmp", None, db_path=p)
        download_update_status(2, "completed", db_path=p)
        queued = download_list(status_filter="queued", db_path=p)
        completed = download_list(status_filter="completed", db_path=p)
        assert len(queued) == 1
        assert len(completed) == 1
