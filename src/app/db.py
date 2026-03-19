"""Re-exports de repositórios (PostgreSQL via DATABASE_URL). Schema e migrações em scripts/schema_postgres.sql."""

from __future__ import annotations

from .repositories.wishlist_repository import (
    add_term as wishlist_add_term,
    delete_by_id as wishlist_delete_by_id,
    get_by_id as wishlist_get_by_id,
    list_all as wishlist_list_all,
)
from .repositories.feed_repository import (
    add_feed_record,
    delete_feed_record,
    get_feed_by_id,
    get_feed_by_url,
    is_processed,
    is_processed_batch,
    list_feed_records,
    mark_processed,
    mark_processed_batch,
    pending_add,
    pending_delete,
    pending_get,
    pending_list,
)
from .repositories.notification_repository import (
    create as notification_create,
    list_notifications as notification_list,
    get_unread_count as notification_unread_count,
    mark_read as notification_mark_read,
    mark_all_read as notification_mark_all_read,
    clear_all as notification_clear_all,
)

__all__ = [
    "add_feed_record",
    "delete_feed_record",
    "list_feed_records",
    "is_processed",
    "is_processed_batch",
    "mark_processed",
    "mark_processed_batch",
    "get_feed_by_url",
    "get_feed_by_id",
    "pending_add",
    "pending_list",
    "pending_get",
    "pending_delete",
    "notification_create",
    "notification_list",
    "notification_unread_count",
    "notification_mark_read",
    "notification_mark_all_read",
    "notification_clear_all",
    "wishlist_add_term",
    "wishlist_list_all",
    "wishlist_get_by_id",
    "wishlist_delete_by_id",
]
