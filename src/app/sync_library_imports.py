"""Scan das pastas de biblioteca (Music/Videos) e importação para library_imports com metadados (ffprobe, iTunes, TMDB).

Rescan = discovery: descobre pastas novas, extrai metadados, busca capas.
NÃO move, renomeia ou reorganiza arquivos (isso é papel do reorganize em Settings).

Scan recursivo inteligente:
- Música: escaneia até 2 níveis (Artist/Album) para importar álbuns individuais
- Vídeos: 1 nível, mas detecta pastas com subpastas de temporada
"""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logger = logging.getLogger(__name__)

_SCAN_MAX_WORKERS = int(os.environ.get("SYNC_MAX_WORKERS", "8"))

MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".webm", ".mov", ".m4v", ".ts", ".m2ts", ".wmv", ".mpg", ".mpeg",
    ".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aiff", ".aac", ".opus", ".wma",
}

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aiff", ".aac", ".opus", ".wma"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".m4v", ".ts", ".m2ts", ".wmv", ".mpg", ".mpeg"}


def _first_media_file(path: Path) -> Path | None:
    if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS:
        return path
    for f in sorted(path.rglob("*")):
        if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS:
            return f
    return None


def _has_media_files(path: Path) -> bool:
    """Verifica rapidamente se a pasta contém pelo menos um arquivo de mídia."""
    if path.is_file():
        return path.suffix.lower() in MEDIA_EXTENSIONS
    for f in path.rglob("*"):
        if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS:
            return True
    return False


def _is_season_folder(name: str) -> bool:
    """Detecta se o nome é uma pasta de temporada (Season 01, S01, Temporada 1, etc.)."""
    return bool(re.match(r"^(Season|Temporada|S)\s*\d{1,2}$", name.strip(), re.I))


def _detect_content_type_from_files(path: Path) -> str:
    """Detecta tipo de conteúdo baseado nos arquivos presentes."""
    has_audio = False
    has_video = False
    for f in path.rglob("*"):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            has_video = True
            break
        if ext in AUDIO_EXTENSIONS:
            has_audio = True
    if has_video:
        return "movies"
    if has_audio:
        return "music"
    return "music"


def _scan_music_path(music_root: Path) -> list[tuple[Path, str]]:
    """Escaneia pasta de música em 2 níveis (Artist/Album).
    - Se Artist/ contém subpastas (álbuns), importa cada álbum
    - Se Artist/ contém diretamente arquivos de mídia, importa o artista inteiro
    """
    results: list[tuple[Path, str]] = []
    if not music_root.is_dir():
        return results

    for artist_dir in sorted(music_root.iterdir()):
        if not artist_dir.is_dir():
            continue

        has_subdirs = any(c.is_dir() for c in artist_dir.iterdir())
        has_direct_media = any(
            c.is_file() and c.suffix.lower() in AUDIO_EXTENSIONS
            for c in artist_dir.iterdir()
        )

        if has_subdirs:
            for album_dir in sorted(artist_dir.iterdir()):
                if album_dir.is_dir() and _has_media_files(album_dir):
                    results.append((album_dir, "music"))
            if has_direct_media:
                results.append((artist_dir, "music"))
        elif has_direct_media:
            results.append((artist_dir, "music"))

    return results


def _scan_videos_path(videos_root: Path) -> list[tuple[Path, str]]:
    """Escaneia pasta de vídeos em 1 nível, detectando séries com Season subfolders."""
    results: list[tuple[Path, str]] = []
    if not videos_root.is_dir():
        return results

    for child in sorted(videos_root.iterdir()):
        if not child.is_dir():
            continue

        subdirs = [c for c in child.iterdir() if c.is_dir()]
        has_season_dirs = any(_is_season_folder(c.name) for c in subdirs)

        if has_season_dirs:
            results.append((child, "tv"))
        elif _has_media_files(child):
            ct = _detect_content_type_from_files(child)
            results.append((child, ct))

    return results


FOLDER_COVER_NAMES = ("folder.jpg", "cover.jpg", "front.jpg", "albumart.jpg", "Folder.jpg", "Cover.jpg")


def _find_folder_cover(folder: Path) -> Path | None:
    """Procura capa na pasta (folder.jpg, cover.jpg, etc.). Retorna Path ou None."""
    if not folder.is_dir():
        return None
    for name in FOLDER_COVER_NAMES:
        p = folder / name
        if p.is_file() and p.stat().st_size > 0:
            return p
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
    """Enriquece um import recém-inserido com ffprobe + capa (thread-safe).
    Para música, também extrai artist/album/genre dos metadados de áudio."""
    from .ffprobe_metadata import extract_metadata
    from .web.cover_service import get_cover_urls

    first_media = _first_media_file(folder)
    artist = None
    album = None
    genre = None
    year = None

    if first_media:
        meta = extract_metadata(first_media)
        title = meta.get("title") or meta.get("album") or name
        if meta.get("year"):
            try:
                year = int(str(meta["year"])[:4])
            except (ValueError, TypeError):
                pass
        artist = meta.get("artist")
        album = meta.get("album")
        genre = meta.get("genre")

        if content_type == "music" and first_media.suffix.lower() in AUDIO_EXTENSIONS:
            try:
                from .audio_metadata import read_audio_metadata
                audio_meta = read_audio_metadata(first_media)
                artist = audio_meta.album_artist or audio_meta.artist or artist
                album = audio_meta.album or album
                genre = audio_meta.genre or genre
                if audio_meta.year:
                    year = audio_meta.year
            except Exception:
                pass

        import_repo.update_metadata(
            import_id,
            name=title,
            year=year,
            metadata_json=meta,
            artist=artist,
            album=album,
            genre=genre,
        )
        name = title

    covers_path.mkdir(parents=True, exist_ok=True)
    small_path = None
    large_path = None
    cover_source: str | None = None

    folder_cover = _find_folder_cover(folder)
    if folder_cover:
        import shutil
        small_file = covers_path / f"import_{import_id}_small.jpg"
        large_file = covers_path / f"import_{import_id}_large.jpg"
        try:
            shutil.copy2(folder_cover, small_file)
            shutil.copy2(folder_cover, large_file)
            small_path = f"import_{import_id}_small.jpg"
            large_path = f"import_{import_id}_large.jpg"
            cover_source = "folder"
        except OSError:
            pass

    if not cover_source and first_media and first_media.suffix.lower() in AUDIO_EXTENSIONS:
        try:
            from .audio_metadata import extract_cover_art
            extracted = extract_cover_art(first_media)
            if extracted:
                data, _ = extracted
                small_file = covers_path / f"import_{import_id}_small.jpg"
                large_file = covers_path / f"import_{import_id}_large.jpg"
                with open(small_file, "wb") as f:
                    f.write(data)
                with open(large_file, "wb") as f:
                    f.write(data)
                small_path = f"import_{import_id}_small.jpg"
                large_path = f"import_{import_id}_large.jpg"
                cover_source = "embedded"
        except Exception:
            pass

    if not cover_source:
        urls = get_cover_urls(content_type, name or folder.name)
        if urls.url_small:
            small_file = covers_path / f"import_{import_id}_small.jpg"
            if _download_cover(urls.url_small, small_file):
                small_path = f"import_{import_id}_small.jpg"
                cover_source = "itunes" if content_type == "music" else "tmdb"
        if urls.url_large and urls.url_large != urls.url_small:
            large_file = covers_path / f"import_{import_id}_large.jpg"
            if _download_cover(urls.url_large, large_file):
                large_path = f"import_{import_id}_large.jpg"
        elif small_path:
            large_path = small_path

    if small_path or large_path:
        import_repo.update_metadata(
            import_id,
            cover_path_small=small_path,
            cover_path_large=large_path,
            cover_source=cover_source,
        )


def run_library_import_scan() -> tuple[int, int]:
    """
    Varre LIBRARY_MUSIC_PATH e LIBRARY_VIDEOS_PATH, adiciona pastas novas a library_imports,
    enriquece com ffprobe e capa (iTunes/TMDB) em paralelo.
    Remove importados cujo content_path não existe mais.

    Este é o RESCAN (discovery): apenas descobre e cataloga.
    NÃO move nem renomeia arquivos.

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
        paths_to_scan.extend(_scan_music_path(p))

    if videos_path:
        p = Path(videos_path).expanduser().resolve()
        paths_to_scan.extend(_scan_videos_path(p))

    logger.info("  [import] Pastas a verificar: %d (music + videos).", len(paths_to_scan))

    candidate_paths = [
        (folder, content_type)
        for folder, content_type in paths_to_scan
        if str(folder.resolve()) not in existing_content_paths
    ]
    if candidate_paths:
        candidate_strs = [str(f.resolve()) for f, _ in candidate_paths]
        already_imported = import_repo.get_existing_content_paths(candidate_strs)
        candidate_paths = [
            (f, ct) for f, ct in candidate_paths
            if str(f.resolve()) not in already_imported
        ]

    new_imports: list[tuple[int, Path, str, str]] = []
    if candidate_paths:
        batch_items = [
            (str(folder.resolve()), content_type, folder.name)
            for folder, content_type in candidate_paths
        ]
        inserted = import_repo.add_batch(batch_items)
        folder_map = {str(f.resolve()): f for f, _ in candidate_paths}
        for import_id, content_path, ct, name in inserted:
            added += 1
            logger.info("  [import] + %s (%s): %s", name, ct, content_path)
            existing_content_paths.add(content_path)
            new_imports.append((import_id, folder_map[content_path], name, ct))

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

    if added > 0 or removed > 0:
        try:
            from .event_bus import CACHE_FACETS_PREFIX, CHANNEL_LIBRARY, cache_delete_pattern, publish
            publish(CHANNEL_LIBRARY, {
                "type": "sync_completed",
                "added": added,
                "removed": removed,
                "facets_dirty": True,
            })
            cache_delete_pattern(f"{CACHE_FACETS_PREFIX}:*")
        except Exception:
            pass

    return added, removed
