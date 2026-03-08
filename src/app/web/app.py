"""FastAPI da API Web: busca, capas, proxy Runner, SPA."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from .routers import cover_router, downloads_router, feeds_router, indexers_router, library_router, notifications_router, radio_router, search_router, settings_router, wishlist_router


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from ..config import get_settings
    s = get_settings()
    db_url = (s.database_url or "").strip()
    if not db_url:
        import logging
        logging.getLogger(__name__).warning("DATABASE_URL não configurado — operações de banco vão falhar")
    else:
        from ..db_postgres import get_async_pool
        await get_async_pool(db_url)
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api.include_router(search_router)
api.include_router(indexers_router)
api.include_router(cover_router)
api.include_router(downloads_router)
api.include_router(wishlist_router)
api.include_router(feeds_router)
api.include_router(notifications_router)
api.include_router(library_router)
api.include_router(radio_router)
api.include_router(settings_router)
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


@app.get("/settings", include_in_schema=False)
def settings_spa():
    return _serve_spa_index()


@app.get("/play", include_in_schema=False)
def play_spa():
    return _serve_spa_index()


if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="atum-assets")
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="atum")
