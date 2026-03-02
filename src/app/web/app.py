"""FastAPI da API Web: busca, capas, proxy Runner, SPA."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from .routers import cover_router, downloads_router, search_router

app = FastAPI(title="dl-torrent Web API", version="0.1.0")
api = APIRouter(prefix="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api.include_router(search_router)
api.include_router(cover_router)
api.include_router(downloads_router)
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


if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="atum-assets")
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="atum")
