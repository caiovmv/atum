"""Routers da API Web (search, cover, downloads, wishlist, feeds, notifications, library, indexers, radio, settings, chat, playlist, recommendations, ai_prompts)."""

from .ai_prompts import router as ai_prompts_router
from .chat import router as chat_router
from .cover import router as cover_router
from .downloads import router as downloads_router
from .feeds import router as feeds_router
from .indexers import router as indexers_router
from .library import router as library_router
from .notifications import router as notifications_router
from .playlist import router as playlist_router
from .radio import router as radio_router
from .recommendations import router as recommendations_router
from .search import router as search_router
from .settings import router as settings_router
from .voice import router as voice_router
from .wishlist import router as wishlist_router

__all__ = ["ai_prompts_router", "chat_router", "search_router", "cover_router", "downloads_router", "wishlist_router", "feeds_router", "notifications_router", "library_router", "indexers_router", "radio_router", "settings_router", "playlist_router", "recommendations_router", "voice_router"]
