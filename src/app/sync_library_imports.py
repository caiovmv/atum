"""Scan das pastas de biblioteca (Music/Videos) e importação para library_imports com metadados (ffprobe, iTunes, TMDB)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logger = logging.getLogger(__name__)

_SCAN_MAX_WORKERS = 4

MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".webm", ".mov", ".m4v", ".ts", ".m2ts", ".wmv", ".mpg", ".mpeg",
    ".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aiff", ".aac", ".opus", ".wma",
}


def _first_media_file(path: Path) -> Path | None:
    if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS:
        return path
    for f in sorted(path.rglob("*")):
        if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS:
            return f
    return None


def _download_cover(url: str, dest_path: Path) -> bool:
    try:
        import requests
        r = requests.get(url, timeout=10, stream=True)
        if r.status_code != 200:
            return False
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception:
        return False


def _enrich_import(
    import_id: int,
    folder: Path,
    name: str,
    content_type: str,
    import_repo,
    covers_path: Path,
) -> None:
    """Enriquece um import recém-inserido com ffprobe + capa (thread-safe)."""
    from .ffprobe_metadata import extract_metadata
    from .web.cover_service import get_cover_urls

    first_media = _first_media_file(folder)
    if first_media:
        meta = extract_metadata(first_media)
        title = meta.get("title") or meta.get("album") or name
        year = None
        if meta.get("year"):
            try:
                year = int(str(meta["year"])[:4])
            except (ValueError, TypeError):
                pass
        import_repo.update_metadata(
            import_id,
            name=title,
            year=year,
            metadata_json=meta,
            artist=meta.get("artist"),
            album=meta.get("album"),
            genre=meta.get("genre"),
        )
        name = title

    urls = get_cover_urls(content_type, name or folder.name)
    covers_path.mkdir(parents=True, exist_ok=True)
    small_path = None
    large_path = None
    if urls.url_small:
        small_file = covers_path / f"import_{import_id}_small.jpg"
        if _download_cover(urls.url_small, small_file):
            small_path = str(small_file)
    if urls.url_large and urls.url_large != urls.url_small:
        large_file = covers_path / f"import_{import_id}_large.jpg"
        if _download_cover(urls.url_large, large_file):
            large_path = str(large_file)
    elif small_path:
        large_path = small_path
    if small_path or large_path:
        import_repo.update_metadata(
            import_id,
            cover_path_small=small_path,
            cover_path_large=large_path,
        )


def run_library_import_scan() -> tuple[int, int]:
    """
    Varre LIBRARY_MUSIC_PATH e LIBRARY_VIDEOS_PATH, adiciona pastas novas a library_imports,
    enriquece com ffprobe e capa (iTunes/TMDB) em paralelo.
    Remove importados cujo content_path não existe mais.
    Retorna (added_count, removed_count).
    """
    from .deps import get_library_import_repo, get_repo, get_settings

    settings = get_settings()
    repo = get_repo()
    import_repo = get_library_import_repo()
    if not import_repo:
        logger.info("  [import] Postgres (library_imports) não configurado; pulando import.")
        return 0, 0

    covers_path = settings.covers_path
    music_path = (settings.library_music_path or "").strip()
    videos_path = (settings.library_videos_path or "").strip()
    if not music_path and not videos_path:
        logger.info("  [import] LIBRARY_MUSIC_PATH e LIBRARY_VIDEOS_PATH não configurados.")
        return 0, 0

    logger.info("  [import] Music: %s | Videos: %s", music_path or "(não definido)", videos_path or "(não definido)")

    existing_content_paths = set()
    for row in repo.list():
        cp = (row.get("content_path") or "").strip()
        if cp:
            existing_content_paths.add(cp)

    added = 0
    paths_to_scan: list[tuple[Path, str]] = []
    if music_path:
        p = Path(music_path).expanduser().resolve()
        if p.is_dir():
            for child in sorted(p.iterdir()):
                if child.is_dir():
                    paths_to_scan.append((child, "music"))
    if videos_path:
        p = Path(videos_path).expanduser().resolve()
        if p.is_dir():
            for child in sorted(p.iterdir()):
                if child.is_dir():
                    paths_to_scan.append((child, "movies"))

    logger.info("  [import] Pastas a verificar: %d (music + videos).", len(paths_to_scan))

    # Fase 1 (sequencial): inserir pastas novas no DB
    new_imports: list[tuple[int, Path, str, str]] = []
    for folder, content_type in paths_to_scan:
        content_path = str(folder.resolve())
        if content_path in existing_content_paths:
            continue
        if import_repo.get_by_content_path(content_path):
            continue
        name = folder.name
        import_id = import_repo.add(
            content_path=content_path,
            content_type=content_type,
            name=name,
        )
        if import_id <= 0:
            continue
        added += 1
        logger.info("  [import] + %s (%s): %s", name, content_type, content_path)
        existing_content_paths.add(content_path)
        new_imports.append((import_id, folder, name, content_type))

    # Fase 2 (paralela): enriquecer com ffprobe + capas
    if new_imports:
        max_workers = min(len(new_imports), _SCAN_MAX_WORKERS)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(
                    _enrich_import, iid, folder, name, ct, import_repo, covers_path,
                ): (iid, name)
                for iid, folder, name, ct in new_imports
            }
            for future in as_completed(futures):
                iid, name = futures[future]
                try:
                    future.result()
                except Exception as exc:
                    logger.warning("  [import] enrich error id=%s (%s): %s", iid, name, exc)

    # Reconcile: remover importados cujo content_path não existe
    removed = 0
    for row in import_repo.list():
        cp = (row.get("content_path") or "").strip()
        if not cp:
            continue
        if Path(cp).exists():
            continue
        iid = row.get("id")
        if iid and import_repo.delete(iid):
            removed += 1
            logger.info("  [import] - removido (path não existe): %s", cp)
        if iid:
            for suffix in ("_small.jpg", "_large.jpg"):
                cover_file = covers_path / f"import_{iid}{suffix}"
                try:
                    if cover_file.is_file():
                        cover_file.unlink()
                except OSError:
                    pass

    return added, removed
