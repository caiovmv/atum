"""Repositórios de persistência (feeds, downloads)."""

from .download_repository import (
    download_add,
    download_delete,
    download_get,
    download_list,
    download_set_pid,
    download_update_status,
)
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
    "download_add",
    "download_list",
    "download_get",
    "download_update_status",
    "download_set_pid",
    "download_delete",
]
