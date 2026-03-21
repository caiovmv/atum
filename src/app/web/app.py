"""FastAPI da API Web: busca, capas, proxy Runner, SPA."""

from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from os import environ
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, Response

from .routers import ai_prompts_router, chat_router, cover_router, downloads_router, feeds_router, indexers_router, library_router, notifications_router, playlist_router, radio_router, recommendations_router, search_router, settings_router, voice_router, wishlist_router


@asynccontextmanager
async def _lifespan(app: FastAPI):
    import logging
    _log = logging.getLogger(__name__)

    from ..config import get_settings
    s = get_settings()
    db_url = (s.database_url or "").strip()
    if not db_url:
        _log.warning("DATABASE_URL não configurado — operações de banco vão falhar")
    else:
        from ..db_postgres import get_async_pool
        await get_async_pool(db_url)

    # Remove caches HLS parciais de transcodificações interrompidas por restart
    try:
        from .hls_service import cleanup_partial_caches
        removed = cleanup_partial_caches()
        if removed:
            _log.info("HLS: %d cache(s) parcial(is) removido(s) na inicialização", removed)
    except Exception:
        _log.exception("HLS: erro ao limpar caches parciais na inicialização")

    yield
    from ..db_postgres import close_all_async_pools, close_all_pools
    await close_all_async_pools()
    close_all_pools()
    from .routers import downloads as _dl_mod, library as _lib_mod
    for mod in (_dl_mod, _lib_mod):
        c = getattr(mod, "_client", None)
        if c and not c.is_closed:
            await c.aclose()


app = FastAPI(title="dl-torrent Web API", version="0.1.0", lifespan=_lifespan)
api = APIRouter(prefix="/api")
_cors_origins_raw = environ.get("CORS_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()] or ["*"]

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _BasicAuthMiddleware(BaseHTTPMiddleware):
    """Exige Authorization: Basic quando BASIC_AUTH_USER e BASIC_AUTH_PASS estão configurados."""

    async def dispatch(self, request: Request, call_next) -> Response:
        from ..config import get_settings

        s = get_settings()
        if not s.basic_auth_user or not s.basic_auth_pass:
            return await call_next(request)

        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        # Preflight CORS e healthcheck sem auth
        if request.method == "OPTIONS" or request.url.path in ("/api/indexers/status",):
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Basic "):
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="Atum"'})

        try:
            raw = base64.b64decode(auth[6:]).decode("utf-8")
            user, _, passwd = raw.partition(":")
            if user != s.basic_auth_user or passwd != s.basic_auth_pass:
                return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="Atum"'})
        except Exception:
            return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="Atum"'})

        return await call_next(request)


app.add_middleware(_BasicAuthMiddleware)

api.include_router(search_router)
api.include_router(indexers_router)
api.include_router(cover_router)
api.include_router(downloads_router)
api.include_router(wishlist_router)
api.include_router(feeds_router)
api.include_router(notifications_router)
api.include_router(library_router)
api.include_router(radio_router)
api.include_router(playlist_router)
api.include_router(voice_router)
api.include_router(settings_router)
api.include_router(chat_router)
api.include_router(recommendations_router)
api.include_router(ai_prompts_router)
app.include_router(api)

# SPA Atum: servir frontend build (npm run build em frontend/)
_frontend_dist = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"


def _serve_spa_index():
    if not _frontend_dist.is_dir():
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(_frontend_dist / "index.html")


@app.get("/", include_in_schema=False)
def root_spa():
    return _serve_spa_index()


@app.get("/downloads", include_in_schema=False)
def downloads_spa():
    return _serve_spa_index()


@app.get("/detail", include_in_schema=False)
def detail_spa():
    return _serve_spa_index()


@app.get("/wishlist", include_in_schema=False)
def wishlist_spa():
    return _serve_spa_index()


@app.get("/feeds", include_in_schema=False)
def feeds_spa():
    return _serve_spa_index()


@app.get("/library", include_in_schema=False)
def library_spa():
    return _serve_spa_index()


@app.get("/radio", include_in_schema=False)
def radio_spa():
    return _serve_spa_index()


@app.get("/playlists", include_in_schema=False)
def playlists_spa():
    return _serve_spa_index()


@app.get("/playlists/{path:path}", include_in_schema=False)
def playlists_sub_spa():
    return _serve_spa_index()


@app.get("/settings", include_in_schema=False)
def settings_spa():
    return _serve_spa_index()


@app.get("/play", include_in_schema=False)
def play_spa():
    return _serve_spa_index()


@app.get("/play/{path:path}", include_in_schema=False)
def play_sub_spa():
    return _serve_spa_index()


@app.get("/play-receiver/{path:path}", include_in_schema=False)
def play_receiver_spa():
    return _serve_spa_index()


@app.get("/detail/{path:path}", include_in_schema=False)
def detail_sub_spa():
    return _serve_spa_index()


@app.get("/search", include_in_schema=False)
def search_spa():
    return _serve_spa_index()


if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="atum-assets")
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="atum")
