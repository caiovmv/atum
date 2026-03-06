"""Extrai metadados de arquivos de mídia via ffprobe (ffmpeg)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe(path: str | Path, timeout_seconds: int = 30) -> dict | None:
    """
    Executa ffprobe no arquivo e retorna um dict com format, streams e tags.
    Retorna None se o arquivo não existir ou ffprobe falhar.
    """
    path = Path(path)
    if not path.is_file():
        return None
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_format",
                "-show_streams",
                "-print_format", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        return json.loads(out.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, ValueError):
        return None


def extract_metadata(path: str | Path, timeout_seconds: int = 30) -> dict:
    """
    Extrai metadados úteis para a biblioteca: duration, codec, title, album, artist, year.
    Fontes: format.tags e streams[].tags (primeiro áudio ou vídeo).
    Retorna dict com chaves opcionais: duration_seconds, codec, title, album, artist, year.
    """
    raw = probe(path, timeout_seconds=timeout_seconds)
    if not raw:
        return {}

    result = {}
    fmt = raw.get("format") or {}
    streams = raw.get("streams") or []

    # Duração (format ou primeiro stream)
    dur = fmt.get("duration")
    if dur is not None:
        try:
            result["duration_seconds"] = float(dur)
        except (TypeError, ValueError):
            pass
    if "duration_seconds" not in result:
        for s in streams:
            d = s.get("duration")
            if d is not None:
                try:
                    result["duration_seconds"] = float(d)
                    break
                except (TypeError, ValueError):
                    pass

    # Codec do primeiro stream de áudio ou vídeo
    for s in streams:
        if s.get("codec_type") in ("audio", "video"):
            result["codec"] = s.get("codec_name") or s.get("codec_long_name")
            result["codec_type"] = s.get("codec_type")
            break

    def get_tag(obj: dict, key: str) -> str | None:
        tags = obj.get("tags") or {}
        v = tags.get(key) or tags.get(key.upper())
        return (v or "").strip() or None

    # Tags: format primeiro, depois primeiro stream de áudio/vídeo
    for tag_key, result_key in (
        ("title", "title"),
        ("album", "album"),
        ("artist", "artist"),
        ("album_artist", "album_artist"),
        ("genre", "genre"),
        ("date", "year"),
        ("year", "year"),
    ):
        if result_key in result:
            continue
        v = get_tag(fmt, tag_key)
        if not v and streams:
            for s in streams:
                if s.get("codec_type") in ("audio", "video"):
                    v = get_tag(s, tag_key)
                    break
        if v:
            if result_key == "year" and len(v) > 4:
                v = v[:4]
            result[result_key] = v

    # Nome para exibição: title > album + artist > nome do arquivo
    if not result.get("title") and (result.get("album") or result.get("artist")):
        result["title"] = " - ".join(
            x for x in (result.get("artist"), result.get("album")) if x
        )

    return result
