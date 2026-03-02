"""Routers da API Web (search, cover, downloads)."""

from .cover import router as cover_router
from .downloads import router as downloads_router
from .search import router as search_router

__all__ = ["search_router", "cover_router", "downloads_router"]
