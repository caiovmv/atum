"""Rotas de Settings: leitura e escrita de configurações em runtime."""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])

_logger = logging.getLogger(__name__)


def _get_repo():
    from ...repositories.settings_repository import get_settings_repo
    repo = get_settings_repo()
    if not repo:
        raise HTTPException(status_code=503, detail="DATABASE_URL não configurado.")
    return repo


def _get_env_defaults() -> dict[str, Any]:
    """Retorna valores do .env que servem como defaults para settings editáveis."""
    from ...deps import get_settings
    s = get_settings()
    return {
        "tmdb_api_key": s.tmdb_api_key or "",
        "lastfm_api_key": s.lastfm_api_key or "",
        "spotify_client_id": s.spotify_client_id or "",
        "spotify_client_secret": s.spotify_client_secret or "",
        "library_music_path": s.library_music_path or "",
        "library_videos_path": s.library_videos_path or "",
    }


@router.get("")
def get_settings_all() -> dict[str, Any]:
    """Retorna todas as configurações (merge: defaults do .env + overrides do DB). Segredos mascarados."""
    repo = _get_repo()
    result = repo.get_all(mask_sensitive=True)
    env_defaults = _get_env_defaults()
    for k, v in env_defaults.items():
        if not result.get(k):
            if k in {"tmdb_api_key", "lastfm_api_key", "spotify_client_secret"} and v and len(v) > 4:
                result[k] = v[:2] + "*" * (len(v) - 4) + v[-2:]
            else:
                result[k] = v
    return result


class SettingsUpdateBody(BaseModel):
    """Campos para PATCH /api/settings. Qualquer subconjunto de chaves."""
    settings: dict[str, Any]


@router.patch("")
def update_settings(body: SettingsUpdateBody) -> dict[str, Any]:
    """Salva overrides de configuração no DB. Retorna o estado completo atualizado."""
    repo = _get_repo()
    if not body.settings:
        raise HTTPException(status_code=400, detail="Nenhuma configuração enviada.")
    repo.set_many(body.settings)
    return repo.get_all(mask_sensitive=True)


class TestConnectionBody(BaseModel):
    """Corpo para POST /api/settings/test-connection."""
    service: str
    url: str | None = None
    token: str | None = None
    api_key: str | None = None


@router.post("/test-connection")
async def test_connection(body: TestConnectionBody) -> dict[str, Any]:
    """Testa conexão com um serviço externo (Plex, Jellyfin, TMDB, Ollama, OpenRouter)."""
    service = (body.service or "").strip().lower()

    async with httpx.AsyncClient(timeout=10) as client:
        if service == "plex":
            url = (body.url or "").strip().rstrip("/")
            token = (body.token or "").strip()
            if not url or not token:
                return {"ok": False, "error": "URL e Token são obrigatórios."}
            try:
                r = await client.get(
                    f"{url}/identity",
                    headers={"X-Plex-Token": token, "Accept": "application/json"},
                )
                if r.status_code == 200:
                    data = r.json()
                    mc = data.get("MediaContainer", {})
                    name = mc.get("friendlyName", "Plex Server")
                    return {"ok": True, "message": f"Conectado: {name}"}
                return {"ok": False, "error": f"HTTP {r.status_code}"}
            except httpx.HTTPError as e:
                return {"ok": False, "error": str(e)}

        if service == "jellyfin":
            url = (body.url or "").strip().rstrip("/")
            api_key = (body.api_key or body.token or "").strip()
            if not url or not api_key:
                return {"ok": False, "error": "URL e API Key são obrigatórios."}
            try:
                r = await client.get(
                    f"{url}/System/Info",
                    headers={"X-Emby-Token": api_key},
                )
                if r.status_code == 200:
                    data = r.json()
                    name = data.get("ServerName", "Jellyfin Server")
                    return {"ok": True, "message": f"Conectado: {name}"}
                return {"ok": False, "error": f"HTTP {r.status_code}"}
            except httpx.HTTPError as e:
                return {"ok": False, "error": str(e)}

        if service == "tmdb":
            api_key = (body.api_key or "").strip()
            if not api_key:
                return {"ok": False, "error": "API Key é obrigatória."}
            try:
                r = await client.get(
                    "https://api.themoviedb.org/3/configuration",
                    params={"api_key": api_key},
                )
                if r.status_code == 200:
                    return {"ok": True, "message": "TMDB API Key válida."}
                return {"ok": False, "error": f"HTTP {r.status_code} — chave inválida?"}
            except httpx.HTTPError as e:
                return {"ok": False, "error": str(e)}

        if service == "ollama":
            url = (body.url or "").strip().rstrip("/")
            if not url:
                return {"ok": False, "error": "URL é obrigatória (ex: http://ollama:11434)."}
            try:
                r = await client.get(f"{url}/api/tags")
                if r.status_code == 200:
                    models = [m.get("name", "") for m in r.json().get("models", [])]
                    return {"ok": True, "message": f"Ollama conectado. Modelos: {', '.join(models[:5]) or 'nenhum'}"}
                return {"ok": False, "error": f"HTTP {r.status_code}"}
            except httpx.HTTPError as e:
                return {"ok": False, "error": str(e)}

        if service == "openrouter":
            api_key = (body.api_key or "").strip()
            if not api_key:
                return {"ok": False, "error": "API Key é obrigatória."}
            try:
                r = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if r.status_code == 200:
                    return {"ok": True, "message": "OpenRouter API Key válida."}
                return {"ok": False, "error": f"HTTP {r.status_code} — chave inválida?"}
            except httpx.HTTPError as e:
                return {"ok": False, "error": str(e)}

    return {"ok": False, "error": f"Serviço desconhecido: {service}"}


@router.get("/enrichment-stats")
async def get_enrichment_stats() -> dict[str, Any]:
    """Retorna contagem de itens pendentes, enriquecidos e com erro."""
    from ...deps import get_library_import_repo
    repo = get_library_import_repo()
    if not repo:
        return {"pending": 0, "enriched": 0, "errors": 0, "total": 0}

    from ...config import get_settings
    from ...db_postgres import aconnection_postgres
    db_url = get_settings().database_url
    if not db_url:
        return {"pending": 0, "enriched": 0, "errors": 0, "total": 0}

    async with aconnection_postgres(db_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE enriched_at IS NOT NULL AND enrichment_error IS NULL) AS enriched,
                    COUNT(*) FILTER (WHERE enrichment_error IS NOT NULL) AS errors,
                    COUNT(*) FILTER (WHERE enriched_at IS NULL AND enrichment_error IS NULL) AS pending
                FROM library_imports
            """)
            row = await cur.fetchone()

    return {
        "total": row["total"] if row else 0,
        "enriched": row["enriched"] if row else 0,
        "errors": row["errors"] if row else 0,
        "pending": row["pending"] if row else 0,
    }


def _cleanup_empty_import(import_repo, row: dict, details: list[str]) -> None:
    """Remove item importado sem arquivos de midia: apaga pasta, entrada no DB e capas em cache."""
    from ...deps import get_settings

    name = (row.get("name") or "?")[:60]
    iid = row.get("id")
    cp = (row.get("content_path") or "").strip()

    if cp:
        p = Path(cp)
        if p.is_dir():
            try:
                shutil.rmtree(p)
                details.append(f"Limpeza: removida pasta vazia '{name}' ({cp})")
                _logger.info("Removida pasta sem mídia: %s", cp)
            except Exception as e:
                details.append(f"Limpeza: erro ao remover pasta '{name}': {e}")
                _logger.warning("Erro ao remover pasta %s: %s", cp, e)
        elif p.is_file():
            try:
                p.unlink()
                details.append(f"Limpeza: removido arquivo sem mídia '{name}'")
            except Exception as e:
                details.append(f"Limpeza: erro ao remover arquivo '{name}': {e}")

    if iid and import_repo:
        try:
            covers_path = get_settings().covers_path
            for suffix in ("_small.jpg", "_large.jpg"):
                cover_file = covers_path / f"import_{iid}{suffix}"
                try:
                    if cover_file.is_file():
                        cover_file.unlink()
                except OSError:
                    pass
        except Exception as exc:
            _logger.debug("Falha ao limpar capas do import %s: %s", iid, exc)
        import_repo.delete(iid)
        _logger.info("Removida entrada DB library_imports id=%s (%s)", iid, name)


_REORGANIZE_MAX_WORKERS = 4


def _reorganize_library_sync(content_type: str | None, dry_run: bool) -> dict:
    """Lógica síncrona da reorganização (roda em thread separada).

    post_process_download() é paralelizado via ThreadPoolExecutor para
    aproveitar I/O concorrente (TMDB HTTP + filesystem).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from ...deps import get_library_import_repo, get_repo
    from ...domain import DownloadStatus
    from ...post_process import post_process_download

    if content_type and content_type.strip().lower() == "movie":
        content_type = "movies"

    repo = get_repo()
    import_repo = get_library_import_repo()

    processed = 0
    skipped = 0
    errors = 0
    cleaned = 0
    details: list[str] = []

    # --- Downloads: filtrar e processar em paralelo ---
    downloads = repo.list(status_filter=DownloadStatus.COMPLETED.value)
    dl_to_process: list[dict] = []
    for row in downloads:
        ct = (row.get("content_type") or "").strip().lower()
        if content_type and ct != content_type.strip().lower():
            continue
        cp = (row.get("content_path") or "").strip()
        name = (row.get("name") or "").strip()
        if not cp or not name:
            skipped += 1
            continue
        if row.get("post_processed"):
            skipped += 1
            continue
        if dry_run:
            details.append(f"[dry-run] {name} ({ct})")
            processed += 1
            continue
        dl_to_process.append(row)

    if dl_to_process:
        workers = min(len(dl_to_process), _REORGANIZE_MAX_WORKERS)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    post_process_download,
                    row["id"],
                    (row.get("content_path") or "").strip(),
                    (row.get("name") or "").strip(),
                    (row.get("content_type") or "").strip().lower() or None,
                    force=True,
                ): row
                for row in dl_to_process
            }
            for future in as_completed(futures):
                row = futures[future]
                name = (row.get("name") or "").strip()
                try:
                    result = future.result()
                    if result.get("success"):
                        processed += 1
                        details.append(f"OK: {name}")
                    else:
                        skipped += 1
                        details.append(f"Pulado: {name} - {result.get('message', '?')}")
                except Exception as e:
                    errors += 1
                    details.append(f"Erro: {name} - {e}")

    # --- Imports: cleanup sequencial, post-process em paralelo ---
    if import_repo:
        imports = import_repo.list(
            content_type=content_type.strip().lower() if content_type else None,
        )
        imp_to_process: list[dict] = []
        for row in imports:
            cp = (row.get("content_path") or "").strip()
            name = (row.get("name") or "").strip()
            ct = (row.get("content_type") or "music").strip().lower()
            if not cp or not Path(cp).exists():
                _cleanup_empty_import(import_repo, row, details)
                cleaned += 1
                continue
            if dry_run:
                details.append(f"[dry-run] import: {name} ({ct})")
                processed += 1
                continue
            imp_to_process.append(row)

        if imp_to_process:
            workers = min(len(imp_to_process), _REORGANIZE_MAX_WORKERS)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(
                        post_process_download,
                        0,
                        (row.get("content_path") or "").strip(),
                        (row.get("name") or "unknown").strip(),
                        (row.get("content_type") or "music").strip().lower(),
                        force=True,
                    ): row
                    for row in imp_to_process
                }
                for future in as_completed(futures):
                    row = futures[future]
                    cp = (row.get("content_path") or "").strip()
                    name = (row.get("name") or "").strip()
                    try:
                        result = future.result()
                        if result.get("success"):
                            processed += 1
                            if result.get("library_path"):
                                try:
                                    import_repo.update_metadata(
                                        row["id"],
                                        previous_content_path=cp,
                                        content_path=result["library_path"],
                                        tmdb_id=result.get("tmdb_id"),
                                        imdb_id=result.get("imdb_id"),
                                    )
                                except Exception as db_err:
                                    if "unique constraint" in str(db_err).lower() or "duplicate key" in str(db_err).lower():
                                        details.append(f"OK (path conflito ignorado): import {name}")
                                    else:
                                        raise
                            details.append(f"OK: import {name}")
                        else:
                            msg = result.get("message", "")
                            no_media = "nenhum arquivo" in msg.lower()
                            no_organize = "nenhum arquivo para organizar" in msg.lower()
                            if no_media or no_organize:
                                _cleanup_empty_import(import_repo, row, details)
                                cleaned += 1
                            else:
                                skipped += 1
                                details.append(f"Pulado: import {name} - {msg}")
                    except Exception as e:
                        errors += 1
                        details.append(f"Erro: import {name} - {e}")

    try:
        from ...db import notification_create
        body_parts = []
        if cleaned:
            body_parts.append(f"Limpeza: {cleaned}")
        if skipped:
            body_parts.append(f"Pulados: {skipped}")
        if errors:
            body_parts.append(f"Erros: {errors}")
        notification_create(
            "library_reorganized",
            f"Reorganização concluída: {processed} itens",
            body=", ".join(body_parts) if body_parts else None,
            payload={"processed": processed, "skipped": skipped, "errors": errors, "cleaned": cleaned},
        )
    except Exception as exc:
        _logger.debug("Falha ao criar notificação de reorganização: %s", exc)

    return {
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "cleaned": cleaned,
        "dry_run": dry_run,
        "details": details[:200],
    }


@router.post("/reorganize-library")
async def reorganize_library(
    content_type: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Reorganiza a biblioteca existente seguindo o padrão Plex-compatible."""
    return await asyncio.to_thread(_reorganize_library_sync, content_type, dry_run)


@router.get("/plex-sections")
async def get_plex_sections() -> list[dict]:
    """Lista seções (bibliotecas) do Plex para o usuário escolher quais scanear."""
    repo = _get_repo()
    url = (repo.get("plex_url") or "").strip().rstrip("/")
    token = (repo.get("plex_token") or "").strip()
    if not url or not token:
        from ...deps import get_settings
        s = get_settings()
        if not url:
            url = ""
        if not token:
            token = ""
    if not url or not token:
        raise HTTPException(status_code=400, detail="Plex URL e Token não configurados.")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{url}/library/sections",
                headers={"X-Plex-Token": token, "Accept": "application/json"},
            )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail="Erro ao listar seções Plex.")
        data = r.json()
        sections = []
        for d in data.get("MediaContainer", {}).get("Directory", []):
            sections.append({
                "id": d.get("key"),
                "title": d.get("title"),
                "type": d.get("type"),
            })
        return sections
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
