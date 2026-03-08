"""Leitura e escrita de metadados de arquivos de áudio usando mutagen (ID3/MP3, Vorbis/FLAC, MP4/M4A)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    """Metadados extraídos de um arquivo de áudio."""

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    album_artist: str | None = None
    track_number: int | None = None
    disc_number: int | None = None
    disc_total: int | None = None
    year: int | None = None
    genre: str | None = None
    duration_seconds: float | None = None
    bitrate: int | None = None
    sample_rate: int | None = None
    has_cover: bool = False


def _parse_track_number(raw: str | int | None) -> int | None:
    """Converte '3/12', '03', 3 em int."""
    if raw is None:
        return None
    s = str(raw).strip()
    if "/" in s:
        s = s.split("/")[0].strip()
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def _parse_year(raw: str | int | None) -> int | None:
    if raw is None:
        return None
    s = str(raw).strip()[:4]
    try:
        y = int(s)
        return y if 1900 <= y <= 2100 else None
    except (ValueError, TypeError):
        return None


def read_audio_metadata(path: Path | str) -> AudioMetadata:
    """Lê metadados de um arquivo de áudio via mutagen. Suporta MP3, FLAC, M4A, OGG, WAV, AIFF."""
    path = Path(path)
    if not path.is_file():
        return AudioMetadata()

    try:
        import mutagen
    except ImportError:
        logger.debug("mutagen não instalado; pulando leitura de metadados de áudio.")
        return AudioMetadata()

    try:
        audio = mutagen.File(str(path), easy=True)
        if audio is None:
            return AudioMetadata()
    except Exception as e:
        logger.debug("Erro ao ler %s com mutagen: %s", path.name, e)
        return AudioMetadata()

    def _first(key: str) -> str | None:
        vals = audio.get(key)
        if isinstance(vals, list) and vals:
            return str(vals[0]).strip() or None
        if isinstance(vals, str) and vals.strip():
            return vals.strip()
        return None

    result = AudioMetadata(
        title=_first("title"),
        artist=_first("artist"),
        album=_first("album"),
        album_artist=_first("albumartist") or _first("album_artist"),
        genre=_first("genre"),
    )

    result.track_number = _parse_track_number(_first("tracknumber"))
    result.disc_number = _parse_track_number(_first("discnumber"))
    result.disc_total = _parse_track_number(_first("disctotal") or _first("totaldiscs"))
    result.year = _parse_year(_first("date") or _first("year"))

    info = audio.info
    if info:
        if hasattr(info, "length") and info.length:
            result.duration_seconds = float(info.length)
        if hasattr(info, "bitrate") and info.bitrate:
            result.bitrate = int(info.bitrate)
        if hasattr(info, "sample_rate") and info.sample_rate:
            result.sample_rate = int(info.sample_rate)

    result.has_cover = _has_cover_art(path)
    return result


def _has_cover_art(path: Path) -> bool:
    """Verifica se o arquivo tem artwork embedded."""
    try:
        import mutagen
        audio = mutagen.File(str(path))
        if audio is None:
            return False
        # FLAC
        if hasattr(audio, "pictures") and audio.pictures:
            return True
        # MP3 (ID3)
        if hasattr(audio, "tags") and audio.tags:
            for key in audio.tags:
                if str(key).startswith("APIC"):
                    return True
        # MP4/M4A
        if hasattr(audio, "tags") and audio.tags and "covr" in (audio.tags or {}):
            return True
    except Exception:
        pass
    return False


def extract_cover_art(path: Path | str) -> tuple[bytes, str] | None:
    """Extrai artwork embedded. Retorna (data, mime_type) ou None."""
    path = Path(path)
    try:
        import mutagen
        audio = mutagen.File(str(path))
        if audio is None:
            return None
        # FLAC
        if hasattr(audio, "pictures") and audio.pictures:
            pic = audio.pictures[0]
            return pic.data, pic.mime or "image/jpeg"
        # MP3 (ID3)
        if hasattr(audio, "tags") and audio.tags:
            for key in audio.tags:
                if str(key).startswith("APIC"):
                    frame = audio.tags[key]
                    return frame.data, frame.mime or "image/jpeg"
        # MP4/M4A
        if hasattr(audio, "tags") and audio.tags and "covr" in (audio.tags or {}):
            covers = audio.tags["covr"]
            if covers:
                data = bytes(covers[0])
                return data, "image/jpeg"
    except Exception as e:
        logger.debug("Erro ao extrair cover art de %s: %s", path, e)
    return None


def write_audio_metadata(path: Path | str, **kwargs) -> bool:
    """
    Escreve/atualiza metadados no arquivo de áudio.
    kwargs aceitos: title, artist, album, album_artist, track_number, year, genre.
    Suporta MP3 (EasyID3), FLAC, M4A (EasyMP4).
    """
    path = Path(path)
    if not path.is_file():
        return False

    try:
        import mutagen
    except ImportError:
        return False

    try:
        audio = mutagen.File(str(path), easy=True)
        if audio is None:
            return False
    except Exception as e:
        logger.debug("Erro ao abrir %s para escrita: %s", path.name, e)
        return False

    mapping = {
        "title": "title",
        "artist": "artist",
        "album": "album",
        "album_artist": "albumartist",
        "genre": "genre",
        "year": "date",
        "track_number": "tracknumber",
    }

    changed = False
    for kwarg_key, tag_key in mapping.items():
        if kwarg_key not in kwargs:
            continue
        val = kwargs[kwarg_key]
        if val is None:
            continue
        try:
            audio[tag_key] = str(val)
            changed = True
        except Exception:
            pass

    if changed:
        try:
            audio.save()
            return True
        except Exception as e:
            logger.debug("Erro ao salvar tags em %s: %s", path.name, e)
            return False
    return True


def embed_cover_art(path: Path | str, image_data: bytes, mime_type: str = "image/jpeg") -> bool:
    """Embute artwork no arquivo de áudio. Suporta MP3 (ID3), FLAC, MP4/M4A."""
    path = Path(path)
    if not path.is_file():
        return False

    try:
        import mutagen
    except ImportError:
        return False

    ext = path.suffix.lower()

    try:
        if ext == ".mp3":
            from mutagen.id3 import APIC, ID3
            try:
                tags = ID3(str(path))
            except mutagen.id3.ID3NoHeaderError:
                tags = ID3()
            tags.delall("APIC")
            tags.add(APIC(
                encoding=3,
                mime=mime_type,
                type=3,
                desc="Cover",
                data=image_data,
            ))
            tags.save(str(path), v2_version=3)
            return True

        if ext == ".flac":
            from mutagen.flac import FLAC, Picture
            audio = FLAC(str(path))
            pic = Picture()
            pic.data = image_data
            pic.mime = mime_type
            pic.type = 3
            pic.desc = "Cover"
            audio.clear_pictures()
            audio.add_picture(pic)
            audio.save()
            return True

        if ext in (".m4a", ".mp4", ".m4b"):
            from mutagen.mp4 import MP4, MP4Cover
            audio = MP4(str(path))
            fmt = MP4Cover.FORMAT_JPEG if "jpeg" in mime_type or "jpg" in mime_type else MP4Cover.FORMAT_PNG
            audio.tags["covr"] = [MP4Cover(image_data, imageformat=fmt)]
            audio.save()
            return True

    except Exception as e:
        logger.debug("Erro ao embutir cover art em %s: %s", path.name, e)

    return False
