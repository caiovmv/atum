"""Extrai metadados do nome do arquivo/torrent: ano, codecs, qualidade vídeo/áudio/música."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from .quality_video import parse_quality_video
from .quality_video import VideoQualityInfo


# Ano: 1900-ano atual
YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Áudio: codecs e canais
AUDIO_DTS = re.compile(r"\b(dts|dts-?hd|dts-?x)\b", re.I)
AUDIO_AAC = re.compile(r"\baac\b", re.I)
AUDIO_AC3 = re.compile(r"\b(ac3|eac3|dd\+?|dolby\s*digital)\b", re.I)
AUDIO_OPUS = re.compile(r"\bopus\b", re.I)
AUDIO_FLAC = re.compile(r"\bflac\b", re.I)
AUDIO_DUAL = re.compile(r"\b(dual\s*audio|dual\s*audio|dualaudio|dublado)\b", re.I)
AUDIO_CHANNELS = re.compile(r"\b(2\.0|5\.1|7\.1)\b")

# Música: qualidade
MUSIC_FLAC = re.compile(r"\bflac\b", re.I)
MUSIC_320 = re.compile(r"\b(320|320kbps?)\b", re.I)
MUSIC_256 = re.compile(r"\b256\b", re.I)
MUSIC_V0 = re.compile(r"\bv0\b", re.I)
MUSIC_V2 = re.compile(r"\bv2\b", re.I)
MUSIC_LOSSLESS = re.compile(r"\blossless\b", re.I)


@dataclass
class ParsedMetadata:
    """Metadados extraídos do nome do arquivo/torrent."""

    raw_title: str
    cleaned_title: str
    year: int | None
    video: VideoQualityInfo | None
    video_quality_label: str | None
    audio_codec: str | None
    audio_channels: str | None
    is_dual_audio: bool
    music_quality: str | None

    def for_search(self, max_words: int = 8) -> str:
        """Título limpo para busca (ex.: TMDB/iTunes). Já em cleaned_title; pode truncar palavras."""
        words = self.cleaned_title.split()[:max_words]
        return " ".join(words) if words else self.cleaned_title[:80]

    def for_search_fallback(self, max_words: int = 4) -> str:
        """Versão ainda mais enxuta para fallback (ex.: só o nome da série/filme)."""
        words = [w for w in self.cleaned_title.split() if len(w) > 1][:max_words]
        return " ".join(words) if words else self.cleaned_title[:50]


def _normalize_for_cleaned(s: str) -> str:
    """Substitui separadores por espaço e colapsa espaços."""
    s = re.sub(r"[\._\-]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _strip_quality_and_audio_from_title(title: str) -> str:
    """Remove padrões de qualidade, codec, áudio, séries (Season/Sxx/Exx) e ruído do título para busca TMDB/iTunes."""
    s = _normalize_for_cleaned(title)
    # Resoluções e fontes (incl. 8k)
    s = re.sub(
        r"\b(1080p|720p|480p|2160p|4k|8k|uhd|bluray|blu-?ray|bdrip|brrip|web-?dl|webdl|webrip|hdtv|pdtv|cam|ts|telesync|hdts|remux|hdr|sdr)\b",
        "",
        s,
        flags=re.I,
    )
    # Codecs vídeo (incl. HEVC por extenso)
    s = re.sub(
        r"\b(hevc|h\.?265|x265|x264|h\.?264|avc|av1|divx|xvid|vp9|avc1)\b",
        "",
        s,
        flags=re.I,
    )
    # Áudio
    s = re.sub(
        r"\b(dts|dts-?hd|dts-?x|aac|ac3|eac3|dd\+?|opus|flac|dual\s*audio|dublado|2\.0|5\.1|7\.1)\b",
        "",
        s,
        flags=re.I,
    )
    # Música (para não poluir busca de filme/série)
    s = re.sub(r"\b(320|256|v0|v2|lossless|kbps)\b", "", s, flags=re.I)
    # Séries: Season X, S01, S1, E01, e01e02, 1x01
    s = re.sub(r"\bseason\s*\d*\b", "", s, flags=re.I)
    s = re.sub(r"\bS\d{1,2}\b", "", s, flags=re.I)
    s = re.sub(r"\bE\d{1,3}\b", "", s, flags=re.I)
    s = re.sub(r"\be\d{1,3}e\d{1,3}\b", "", s, flags=re.I)
    s = re.sub(r"\b\d+x\d{1,3}\b", "", s, flags=re.I)
    # Edições e ruído
    s = re.sub(
        r"\b(rarbg|yify|yts|web-dl|hdrip|extended|directors?\s*cut|remaster|uncut|repack|proper|fixed|fix)\b",
        "",
        s,
        flags=re.I,
    )
    # Parênteses que sobram (ex.: "(1080p..." truncado) — remove até o fim ou até )
    s = re.sub(r"\s*\([^)]*$", "", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Limpa pontuação e espaços duplos nas bordas
    s = re.sub(r"^\s*[\(\-\:\s]+|\s*[\)\-\:\s]+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_metadata_from_name(name: str) -> ParsedMetadata:
    """
    Analisa o nome (título do torrent ou arquivo) e retorna metadados unificados:
    ano, qualidade de vídeo (reutilizando quality_video), áudio e qualidade de música.
    """
    raw = (name or "").strip()
    if not raw:
        return ParsedMetadata(
            raw_title="",
            cleaned_title="",
            year=None,
            video=None,
            video_quality_label=None,
            audio_codec=None,
            audio_channels=None,
            is_dual_audio=False,
            music_quality=None,
        )

    # Ano: primeiro match plausível (1900 até ano atual)
    year = None
    for m in YEAR_PATTERN.finditer(raw):
        y = int(m.group(1))
        if 1900 <= y <= datetime.now().year:
            year = y
            break

    # Vídeo (reutiliza quality_video)
    video = parse_quality_video(raw)
    video_quality_label = video.label if video and video.raw_title else None

    # Áudio
    audio_codec = None
    if AUDIO_DTS.search(raw):
        audio_codec = "DTS"
    elif AUDIO_AC3.search(raw):
        audio_codec = "AC3"
    elif AUDIO_AAC.search(raw):
        audio_codec = "AAC"
    elif AUDIO_OPUS.search(raw):
        audio_codec = "Opus"
    elif AUDIO_FLAC.search(raw):
        audio_codec = "FLAC"

    audio_channels = None
    ch = AUDIO_CHANNELS.search(raw)
    if ch:
        audio_channels = ch.group(1)

    is_dual_audio = bool(AUDIO_DUAL.search(raw))

    # Música
    music_quality = None
    if MUSIC_FLAC.search(raw) or MUSIC_LOSSLESS.search(raw):
        music_quality = "FLAC"
    elif MUSIC_320.search(raw):
        music_quality = "320"
    elif MUSIC_256.search(raw):
        music_quality = "256"
    elif MUSIC_V0.search(raw):
        music_quality = "V0"
    elif MUSIC_V2.search(raw):
        music_quality = "V2"

    cleaned_title = _strip_quality_and_audio_from_title(raw)
    if not cleaned_title:
        cleaned_title = raw[:80]

    return ParsedMetadata(
        raw_title=raw,
        cleaned_title=cleaned_title,
        year=year,
        video=video,
        video_quality_label=video_quality_label,
        audio_codec=audio_codec,
        audio_channels=audio_channels,
        is_dual_audio=is_dual_audio,
        music_quality=music_quality,
    )
