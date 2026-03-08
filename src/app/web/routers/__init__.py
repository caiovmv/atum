"""Routers da API Web (search, cover, downloads, wishlist, feeds, notifications, library, indexers, radio, settings)."""

from .cover import router as cover_router
from .downloads import router as downloads_router
from .feeds import router as feeds_router
from .indexers import router as indexers_router
from .library import router as library_router
from .notifications import router as notifications_router
from .radio import router as radio_router
from .search import router as search_router
from .settings import router as settings_router
from .wishlist import router as wishlist_router

__all__ = ["search_router", "cover_router", "downloads_router", "wishlist_router", "feeds_router", "notifications_router", "library_router", "indexers_router", "radio_router", "settings_router"]
