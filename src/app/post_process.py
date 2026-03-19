"""Pipeline de pós-processamento: organiza arquivos baixados em estrutura Plex-compatible.

Melhorias sobre a versão anterior:
- Detecção de content_type via guessit (1x01, anime, etc.)
- Copia subtitles (.srt/.sub/.ass/.ssa/.sup/.idx) junto com vídeos
- Trata Various Artists / coletâneas via album_artist
- Detecta edições de filmes (Director's Cut, Extended, etc.)
- Parse de episódio suporta 1x01 além de SxxExx
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

from .audio_metadata import AudioMetadata, read_audio_metadata
from .file_linker import cleanup_empty_dirs, link_or_copy, rename_directory
from .metadata_from_name import parse_metadata_from_name
from .organize import (
    ContentType,
    _detect_edition,
    _guessit_parse,
    _sanitize,
    plex_movie_path,
    plex_music_path,
    plex_tv_path,
)
from .sync_library_imports import MEDIA_EXTENSIONS
from .tmdb_enrichment import EnrichedMetadata, enrich

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".m4v", ".ts", ".m2ts", ".wmv", ".mpg", ".mpeg"}
AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aiff", ".aac", ".opus", ".wma"}
SUBTITLE_EXTENSIONS = {".srt", ".sub", ".ass", ".ssa", ".sup", ".idx", ".vtt"}


def _get_settings_value(key: str, default=None):
    """Obtém valor de uma setting (runtime DB > .env default)."""
    try:
        from .repositories.settings_repository import get_settings_repo
        repo = get_settings_repo()
        if repo:
            v = repo.get(key)
            if v is not None:
                return v
    except Exception:
        pass
    return default


def _detect_content_type(content_path: Path, name: str | None = None) -> ContentType:
    """Infere content_type via guessit com fallback para heurísticas de extensão."""
    title = name or content_path.name

    # guessit: parsing robusto que detecta SxxExx, 1x01, anime, etc.
    g = _guessit_parse(title)
    if g:
        gtype = g.get("type")
        if gtype == "episode":
            return "tv"
        if gtype == "movie":
            has_video = _has_extension_type(content_path, VIDEO_EXTENSIONS)
            if has_video:
                return "movies"

    # Regex patterns: SxxExx, Season X, 1x01
    if re.search(r"S\d{1,2}E\d{1,3}", title, re.I):
        return "tv"
    if re.search(r"Season\s*\d", title, re.I):
        return "tv"
    if re.search(r"\b\d{1,2}x\d{2,3}\b", title, re.I):
        return "tv"

    has_video = _has_extension_type(content_path, VIDEO_EXTENSIONS)
    has_audio = _has_extension_type(content_path, AUDIO_EXTENSIONS)

    if has_video:
        if re.search(r"S\d{1,2}", title, re.I):
            return "tv"
        return "movies"
    if has_audio:
        return "music"

    try:
        from .ai.llm_organize import llm_detect_content_type
        result = llm_detect_content_type(title)
        if result:
            ct, confidence = result
            if confidence >= 0.6:
                return ct  # type: ignore[return-value]
    except Exception:
        pass

    return "music"


def _has_extension_type(content_path: Path, extensions: set[str]) -> bool:
    """Verifica se content_path contém arquivos com as extensões dadas."""
    if content_path.is_file():
        return content_path.suffix.lower() in extensions
    if content_path.is_dir():
        for f in content_path.rglob("*"):
            if f.is_file() and f.suffix.lower() in extensions:
                return True
    return False


def _list_media_files(content_path: Path) -> list[Path]:
    """Lista arquivos de mídia no content_path."""
    if content_path.is_file() and content_path.suffix.lower() in MEDIA_EXTENSIONS:
        return [content_path]
    if content_path.is_dir():
        return sorted(
            f for f in content_path.rglob("*")
            if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS
        )
    return []


def _list_subtitle_files(content_path: Path) -> list[Path]:
    """Lista arquivos de legenda no content_path."""
    if content_path.is_file():
        return []
    if content_path.is_dir():
        return sorted(
            f for f in content_path.rglob("*")
            if f.is_file() and f.suffix.lower() in SUBTITLE_EXTENSIONS
        )
    return []


def _find_subtitle_for_video(video_path: Path, subtitles: list[Path]) -> list[Path]:
    """Encontra legendas associadas a um vídeo (mesmo stem ou stem contido)."""
    video_stem = video_path.stem.lower()
    matches = []
    for sub in subtitles:
        sub_stem = sub.stem.lower()
        if sub_stem == video_stem or sub_stem.startswith(video_stem):
            matches.append(sub)
    return matches


def _parse_episode_info(name: str) -> tuple[int, int, str | None] | None:
    """Extrai season, episode, episode_title. Suporta SxxExx e NxNN."""
    # SxxExx
    m = re.search(r"S(\d{1,2})E(\d{1,3})", name, re.I)
    if m:
        season = int(m.group(1))
        episode = int(m.group(2))
        ep_title = _clean_episode_title(name[m.end():])
        return season, episode, ep_title

    # NxNN (1x01)
    m = re.search(r"\b(\d{1,2})x(\d{2,3})\b", name, re.I)
    if m:
        season = int(m.group(1))
        episode = int(m.group(2))
        ep_title = _clean_episode_title(name[m.end():])
        return season, episode, ep_title

    # guessit fallback
    g = _guessit_parse(name)
    if g and g.get("type") == "episode":
        season = g.get("season", 1)
        episode = g.get("episode")
        if isinstance(episode, list):
            episode = episode[0] if episode else None
        if episode is not None:
            ep_title = g.get("episode_title")
            return int(season), int(episode), ep_title

    return None


def _clean_episode_title(rest: str) -> str | None:
    """Limpa resíduo após pattern de episódio para extrair título."""
    rest = re.sub(r"^[\s\-\.]+", "", rest)
    rest = re.sub(r"\.\w{2,4}$", "", rest)
    rest = re.sub(r"\[.*$", "", rest)
    rest = re.sub(
        r"\b(1080p|720p|480p|2160p|4k|8k|bluray|webrip|web-dl|hdtv|x264|x265|hevc|avc|"
        r"aac|ac3|dts|dts-hd|atmos|truehd|flac|opus|remux|hdr|sdr)\b.*",
        "", rest, flags=re.I,
    )
    return rest.strip() or None


def _is_same_or_parent(a: Path, b: Path) -> bool:
    """Verifica se 'a' é igual ou pai de 'b'."""
    try:
        a_resolved = a.resolve()
        b_resolved = b.resolve()
        return a_resolved == b_resolved or b_resolved in a_resolved.parents
    except (OSError, ValueError):
        return False


_LIBRARY_ROOT_NAMES = frozenset({
    "music", "movies", "tv", "videos", "library", "downloads",
    "media", "series", "shows", "films", "audio",
})


def _extract_artist_album_fallback(title: str, path: Path, base_path: Path | None = None) -> tuple[str, str]:
    """Extrai artist/album do titulo ou nome da pasta quando metadados de audio não existem.
    Normaliza separadores e trata prefixos de label."""
    name = title or path.name
    name = re.sub(r"[\._]", " ", name)
    name = re.sub(r"\s*\[[^\]]*\]\s*", " ", name)
    name = re.sub(r"\s*\([^)]*\)\s*", " ", name)
    name = re.sub(r"^\s*[\[\{][^\]\}]*[\]\}]\s*", "", name)
    name = re.sub(r"\s+", " ", name).strip()

    for sep in [" - ", " – ", " — ", " − "]:
        if sep in name:
            parts = name.split(sep, 1)
            artist = _sanitize(parts[0].strip()) or "Unknown Artist"
            album = _sanitize(parts[1].strip()) or name
            return artist, album

    if path.is_dir() and path.parent.name and path.parent.name != path.name:
        parent_is_root = (
            (base_path is not None and path.parent == base_path)
            or path.parent.name.lower() in _LIBRARY_ROOT_NAMES
        )
        if not parent_is_root:
            return _sanitize(path.parent.name) or "Unknown Artist", _sanitize(name) or "Unknown Album"

    return "Unknown Artist", _sanitize(name) or "Unknown Album"


def _infer_disc_numbers(
    entries: list[tuple[Path, AudioMetadata, str, str]],
) -> None:
    """Detecta álbuns multi-disco sem tags de disc e atribui disc_number inferido."""
    albums: dict[tuple[str, str], list[tuple[Path, AudioMetadata]]] = defaultdict(list)
    for mf, meta, artist, album in entries:
        albums[(artist, album)].append((mf, meta))

    for (_artist, _album), files in albums.items():
        all_have_disc = all(m.disc_number is not None for _, m in files)

        if all_have_disc:
            disc_nums = {m.disc_number for _, m in files}
            if len(disc_nums) > 1:
                inferred_total = max(disc_nums)
                for _, m in files:
                    if m.disc_total is None:
                        m.disc_total = inferred_total
            continue

        track_counts: dict[int | None, int] = defaultdict(int)
        for _, m in files:
            track_counts[m.track_number] += 1

        has_duplicates = any(c > 1 for tn, c in track_counts.items() if tn is not None)
        if not has_duplicates:
            continue

        sorted_files = sorted(files, key=lambda x: x[0].name)
        max_dupes = max(c for tn, c in track_counts.items() if tn is not None and c > 1)

        seen: dict[int | None, int] = defaultdict(int)
        for mf, meta in sorted_files:
            seen[meta.track_number] += 1
            meta.disc_number = seen[meta.track_number]
            meta.disc_total = max_dupes

        logger.info(
            "Multi-disco inferido para %s / %s: %d discos, %d faixas",
            _artist, _album, max_dupes, len(files),
        )


def _resolve_artist_for_compilation(
    entries: list[tuple[Path, AudioMetadata, str, str]],
) -> list[tuple[Path, AudioMetadata, str, str]]:
    """Detecta coletâneas (Various Artists) usando album_artist ou variação de artistas.
    Se album_artist existe e é diferente do artist individual, usa album_artist como artista da pasta."""
    if not entries:
        return entries

    artists = {artist for _, _, artist, _ in entries}
    albums = {album for _, _, _, album in entries}

    if len(albums) == 1 and len(artists) > 3:
        album_artists = {
            meta.album_artist for _, meta, _, _ in entries
            if meta.album_artist and meta.album_artist.strip()
        }
        va_artist = "Various Artists"
        if album_artists:
            va_artist = _sanitize(next(iter(album_artists)).strip())
        return [(mf, meta, va_artist, album) for mf, meta, _, album in entries]

    result = []
    for mf, meta, artist, album in entries:
        if meta.album_artist and meta.album_artist.strip():
            aa = meta.album_artist.strip().lower()
            if aa in ("various artists", "va", "various", "compilation"):
                result.append((mf, meta, "Various Artists", album))
            else:
                result.append((mf, meta, _sanitize(meta.album_artist.strip()), album))
        else:
            result.append((mf, meta, artist, album))
    return result


def post_process_download(
    download_id: int,
    content_path: str,
    name: str | None = None,
    content_type: str | None = None,
    force: bool = False,
) -> dict:
    """
    Pipeline de pós-processamento para um download concluído.
    Retorna dict com: success, library_path, tmdb_id, imdb_id, content_type, message.
    Se force=True, ignora a verificação de post_process_enabled.
    """
    from .deps import get_repo, get_settings

    result = {
        "success": False,
        "library_path": None,
        "tmdb_id": None,
        "imdb_id": None,
        "content_type": content_type,
        "artist": None,
        "album": None,
        "genre": None,
        "message": "",
    }

    if not force:
        enabled = _get_settings_value("post_process_enabled", True)
        if not enabled:
            result["message"] = "Pós-processamento desabilitado."
            return result

    path = Path(content_path)
    if not path.exists():
        result["message"] = f"Content path não existe: {content_path}"
        return result

    title = name or path.name
    ct: ContentType = content_type if content_type in ("music", "movies", "tv", "concerts") else _detect_content_type(path, title)  # type: ignore[assignment]
    result["content_type"] = ct

    plex_naming = _get_settings_value("plex_naming_enabled", True)
    organize_mode = _get_settings_value("organize_mode", "in_place")
    include_tmdb = _get_settings_value("include_tmdb_id_in_folder", True)
    include_imdb = _get_settings_value("include_imdb_id_in_folder", False)

    settings = get_settings()
    if ct in ("music", "concerts"):
        base_path = Path(settings.library_music_path or settings.save_path_for_content_type("music"))
    else:
        base_path = Path(settings.library_videos_path or settings.save_path_for_content_type(ct))

    enriched: EnrichedMetadata | None = None
    if ct in ("movies", "tv"):
        try:
            enriched = enrich(title, ct)
            result["tmdb_id"] = enriched.tmdb_id
            result["imdb_id"] = enriched.imdb_id
        except Exception as e:
            logger.warning("Erro ao enriquecer %s: %s", title, e)

    media_files = _list_media_files(path)
    if not media_files:
        result["message"] = "Nenhum arquivo de mídia encontrado."
        return result

    if not plex_naming:
        result["success"] = True
        result["library_path"] = content_path
        result["message"] = "Plex naming desabilitado; mantendo estrutura original."
        _update_download_record(download_id, result, get_repo())
        return result

    new_paths: list[tuple[Path, Path]] = []
    subtitle_files = _list_subtitle_files(path) if ct in ("movies", "tv") else []

    if ct == "movies":
        main_file = max(media_files, key=lambda f: f.stat().st_size)
        e_title = (enriched.title if enriched else None) or title
        e_year = (enriched.year if enriched else None)
        tmdb_id = enriched.tmdb_id if enriched else None
        imdb_id = enriched.imdb_id if enriched else None
        edition = _detect_edition(title)
        if not e_year:
            parsed = parse_metadata_from_name(title)
            e_year = parsed.year
        rel = plex_movie_path(
            e_title, e_year, main_file.suffix,
            tmdb_id=tmdb_id, imdb_id=imdb_id,
            include_tmdb=include_tmdb, include_imdb=include_imdb,
            edition=edition,
        )
        dst = base_path / rel
        new_paths.append((main_file, dst))

        for sub in _find_subtitle_for_video(main_file, subtitle_files):
            sub_dst = dst.parent / sub.name
            new_paths.append((sub, sub_dst))

    elif ct == "tv":
        show_name = (enriched.title if enriched else None) or title
        show_year = enriched.year if enriched else None
        tmdb_id = enriched.tmdb_id if enriched else None
        imdb_id = enriched.imdb_id if enriched else None
        show_name_clean = re.sub(r"\s*S\d+.*$", "", show_name, flags=re.I).strip()
        if not show_name_clean:
            show_name_clean = show_name

        for mf in media_files:
            ep_info = _parse_episode_info(mf.name)
            if not ep_info:
                ep_info = _parse_episode_info(title)
            if ep_info:
                season, episode, ep_title = ep_info
                rel = plex_tv_path(
                    show_name_clean, season, episode, ep_title,
                    year=show_year, ext=mf.suffix,
                    tmdb_id=tmdb_id, imdb_id=imdb_id,
                    include_tmdb=include_tmdb, include_imdb=include_imdb,
                )
                dst = base_path / rel
                new_paths.append((mf, dst))

                for sub in _find_subtitle_for_video(mf, subtitle_files):
                    sub_dst = dst.parent / sub.name
                    new_paths.append((sub, sub_dst))
            else:
                logger.debug("Não foi possível parsear episódio de: %s", mf.name)

    elif ct in ("music", "concerts"):
        fallback_artist, fallback_album = _extract_artist_album_fallback(title, path, base_path)
        audio_entries: list[tuple[Path, AudioMetadata, str, str]] = []
        for mf in media_files:
            if mf.suffix.lower() in AUDIO_EXTENSIONS:
                meta = read_audio_metadata(mf)
                artist = meta.artist or fallback_artist
                album = meta.album or fallback_album

                if not meta.artist or not meta.album:
                    try:
                        from .ai.llm_organize import llm_fix_audio_metadata
                        fixed = llm_fix_audio_metadata(
                            mf.name,
                            existing_artist=meta.artist,
                            existing_album=meta.album,
                            existing_title=meta.title,
                            existing_year=meta.year,
                            existing_genre=meta.genre,
                            folder_path=str(mf.parent),
                        )
                        if fixed:
                            if not meta.artist and fixed.get("artist"):
                                artist = fixed["artist"]
                            if not meta.album and fixed.get("album"):
                                album = fixed["album"]
                            if not meta.genre and fixed.get("genre"):
                                meta.genre = fixed["genre"]
                    except Exception:
                        pass

                audio_entries.append((mf, meta, artist, album))
            else:
                logger.debug("Pulando arquivo não-áudio: %s", mf.name)

        audio_entries = _resolve_artist_for_compilation(audio_entries)
        _infer_disc_numbers(audio_entries)

        if audio_entries:
            result["artist"] = audio_entries[0][2]
            result["album"] = audio_entries[0][3]
            genres = {meta.genre for _, meta, _, _ in audio_entries if meta.genre}
            if genres:
                result["genre"] = next(iter(genres))

        for mf, meta, artist, album in audio_entries:
            rel = plex_music_path(
                artist, album, meta.year, meta.track_number,
                meta.title or mf.stem, mf.suffix,
                disc_number=meta.disc_number, disc_total=meta.disc_total,
            )
            dst = base_path / rel
            new_paths.append((mf, dst))

    if not new_paths:
        result["message"] = "Nenhum arquivo para organizar."
        return result

    success_count = 0
    for src, dst in new_paths:
        if src == dst:
            success_count += 1
            continue
        ok = link_or_copy(src, dst, mode=organize_mode)
        if ok:
            success_count += 1
        else:
            logger.warning("Falha ao organizar: %s -> %s", src, dst)

    if success_count > 0:
        first_dst = new_paths[0][1]
        if ct == "music":
            result["library_path"] = str(first_dst.parent.parent)
        elif ct == "tv":
            result["library_path"] = str(first_dst.parent.parent)
        else:
            result["library_path"] = str(first_dst.parent)

    if organize_mode == "in_place" and success_count > 0:
        old_dir = path if path.is_dir() else path.parent
        if old_dir.is_dir() and old_dir != base_path and not _is_same_or_parent(old_dir, base_path):
            cleanup_empty_dirs(old_dir, stop_at=base_path)

    result["success"] = success_count > 0
    result["message"] = f"{success_count}/{len(new_paths)} arquivo(s) organizados."

    _update_download_record(download_id, result, get_repo())
    _trigger_media_server_scan(ct)

    _notify_post_process(result, title)

    return result


def _notify_post_process(result: dict, title: str) -> None:
    """Cria notificação de pós-processamento."""
    try:
        from .db import notification_create
        if result.get("success"):
            notification_create(
                "post_process_completed",
                f"Biblioteca organizada: {title[:80]}",
                body=result.get("message"),
                payload={"content_type": result.get("content_type"), "tmdb_id": result.get("tmdb_id")},
            )
        else:
            msg = result.get("message", "Erro desconhecido")
            notification_create(
                "post_process_failed",
                f"Erro ao organizar: {title[:60]}",
                body=msg[:200],
            )
    except Exception:
        logger.debug("Falha ao criar notificação de pós-processamento", exc_info=True)


def _update_download_record(download_id: int, result: dict, repo) -> None:
    """Atualiza o registro de download no DB com dados do pós-processamento."""
    try:
        updates = {}
        if result.get("library_path"):
            updates["library_path"] = result["library_path"]
        if result.get("tmdb_id"):
            updates["tmdb_id"] = result["tmdb_id"]
        if result.get("imdb_id"):
            updates["imdb_id"] = result["imdb_id"]
        if result.get("content_type"):
            updates["content_type"] = result["content_type"]
        if result.get("artist"):
            updates["artist"] = result["artist"]
        if result.get("album"):
            updates["album"] = result["album"]
        if result.get("genre"):
            updates["genre"] = result["genre"]
        updates["post_processed"] = result.get("success", False)

        _ALLOWED_COLUMNS = {"library_path", "tmdb_id", "imdb_id", "content_type", "post_processed", "artist", "album", "genre"}
        if updates and hasattr(repo, "update_enrichment"):
            repo.update_enrichment(download_id, **updates)
        elif updates:
            safe_updates = {k: v for k, v in updates.items() if k in _ALLOWED_COLUMNS}
            if safe_updates:
                try:
                    from .db_postgres import connection_postgres
                    from .deps import get_settings
                    db_url = get_settings().database_url
                    if db_url:
                        set_clause = ", ".join(f"{col} = %s" for col in safe_updates)
                        values = list(safe_updates.values())
                        values.append(download_id)
                        with connection_postgres(db_url) as conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    f"UPDATE downloads SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                                    values,
                                )
                                conn.commit()
                except Exception as exc:
                    logger.debug("Falha ao atualizar download %s: %s", download_id, exc)
    except Exception as e:
        logger.warning("Erro ao atualizar registro de download %s: %s", download_id, e)


def _trigger_media_server_scan(content_type: str) -> None:
    """Dispara scan no Plex/Jellyfin se configurado."""
    import requests as req

    from .db import notification_create

    plex_auto = _get_settings_value("plex_auto_scan", False)
    if plex_auto:
        plex_url = _get_settings_value("plex_url", "")
        plex_token = _get_settings_value("plex_token", "")
        section_ids = _get_settings_value("plex_section_ids", "")
        if plex_url and plex_token and section_ids:
            ids = [s.strip() for s in str(section_ids).split(",") if s.strip()]
            for sid in ids:
                try:
                    url = f"{plex_url.rstrip('/')}/library/sections/{sid}/refresh"
                    req.get(url, headers={"X-Plex-Token": plex_token}, timeout=10)
                    logger.info("Plex scan disparado para seção %s.", sid)
                    try:
                        notification_create("plex_scan", f"Scan Plex disparado (seção {sid})")
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning("Erro ao disparar scan Plex seção %s: %s", sid, e)
                    try:
                        notification_create("media_scan_failed", f"Erro ao scanear Plex seção {sid}", body=str(e)[:200])
                    except Exception:
                        pass

    jellyfin_auto = _get_settings_value("jellyfin_auto_scan", False)
    if jellyfin_auto:
        jf_url = _get_settings_value("jellyfin_url", "")
        jf_key = _get_settings_value("jellyfin_api_key", "")
        if jf_url and jf_key:
            try:
                req.post(
                    f"{jf_url.rstrip('/')}/Library/Refresh",
                    headers={"X-Emby-Token": jf_key},
                    timeout=10,
                )
                logger.info("Jellyfin scan disparado.")
                try:
                    notification_create("jellyfin_scan", "Scan Jellyfin disparado")
                except Exception:
                    pass
            except Exception as e:
                logger.warning("Erro ao disparar scan Jellyfin: %s", e)
                try:
                    notification_create("media_scan_failed", "Erro ao scanear Jellyfin", body=str(e)[:200])
                except Exception:
                    pass
