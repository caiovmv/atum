"""Download Runner: processo FastAPI que expõe a fila de downloads via HTTP (para API Web e CLI remoto)."""

from .app import app

__all__ = ["app"]
