"""Repositórios de persistência (feeds, downloads)."""

from .feed_repository import (
    add_feed_record,
    get_feed_by_id,
    get_feed_by_url,
    is_processed,
    list_feed_records,
    mark_processed,
)

__all__ = [
    "add_feed_record",
    "list_feed_records",
    "is_processed",
    "mark_processed",
    "get_feed_by_url",
    "get_feed_by_id",
]
