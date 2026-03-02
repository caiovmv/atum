"""Parser de qualidade de vídeo no título do torrent (resolução, codec, fonte) e score para ordenação."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Literal

# Score para ordenação (maior = melhor). Resolução domina; codec e source dão bônus.
class VideoQualityScore(IntEnum):
    UNKNOWN = 0
    P720 = 10   # 720p
    P1080 = 20  # 1080p
    P2160 = 30  # 2160p/4K


VideoQualityKind = Literal["720p", "1080p", "2160p", "4k", "unknown"]

# Fonte: influencia score secundário (BluRay/WEB-DL preferível a HDTV/CAM)
SOURCE_BLURAY = "bluray"
SOURCE_WEBDL = "webdl"
SOURCE_HDTV = "hdtv"
SOURCE_CAM = "cam"


@dataclass
class VideoQualityInfo:
    """Resultado do parser de qualidade de vídeo a partir do título."""

    kind: VideoQualityKind
    score: int
    resolution_p: int | None  # 720, 1080, 2160
    codec: str | None  # x264, x265, etc.
    source: str | None  # bluray, webdl, hdtv, cam
    raw_title: str

    @property
    def label(self) -> str:
        parts = []
        if self.resolution_p:
            parts.append(f"{self.resolution_p}p")
        if self.codec:
            parts.append(self.codec.upper())
        if self.source:
            parts.append(self.source.upper())
        return " ".join(parts) if parts else "?"


# Padrões para resolução (case-insensitive)
P2160_PATTERN = re.compile(r"\b(2160p|4k|4K|uhd)\b", re.I)
P1080_PATTERN = re.compile(r"\b1080p\b", re.I)
P720_PATTERN = re.compile(r"\b720p\b", re.I)

# Codec
X265_PATTERN = re.compile(r"\b(hevc|x265|h\.?265)\b", re.I)
X264_PATTERN = re.compile(r"\b(x264|h\.?264|avc)\b", re.I)

# Fonte
BLURAY_PATTERN = re.compile(r"\b(bluray|blu-?ray|bdrip|brrip)\b", re.I)
WEBDL_PATTERN = re.compile(r"\b(web-?dl|webdl|webrip)\b", re.I)
HDTV_PATTERN = re.compile(r"\b(hdtv|pdtv)\b", re.I)
CAM_PATTERN = re.compile(r"\b(cam|ts|telesync|hdts)\b", re.I)


def parse_quality_video(title: str) -> VideoQualityInfo:
    """
    Analisa o título do torrent e retorna qualidade de vídeo (resolução, codec, fonte).
    Ordem de preferência: 2160p > 1080p > 720p; codec e fonte como secundários.
    """
    raw = title.strip()
    if not raw:
        return VideoQualityInfo(
            kind="unknown",
            score=VideoQualityScore.UNKNOWN,
            resolution_p=None,
            codec=None,
            source=None,
            raw_title=raw,
        )

    resolution_p: int | None = None
    kind: VideoQualityKind = "unknown"
    score = VideoQualityScore.UNKNOWN

    if P2160_PATTERN.search(raw):
        resolution_p = 2160
        kind = "2160p"
        score = VideoQualityScore.P2160
    elif P1080_PATTERN.search(raw):
        resolution_p = 1080
        kind = "1080p"
        score = VideoQualityScore.P1080
    elif P720_PATTERN.search(raw):
        resolution_p = 720
        kind = "720p"
        score = VideoQualityScore.P720

    codec: str | None = None
    if X265_PATTERN.search(raw):
        codec = "x265"
        if score > 0:
            score = score + 2  # pequeno bônus sobre x264
    elif X264_PATTERN.search(raw):
        codec = "x264"
        if score > 0:
            score = score + 1

    source: str | None = None
    if BLURAY_PATTERN.search(raw):
        source = SOURCE_BLURAY
        if score > 0:
            score = score + 3
    elif WEBDL_PATTERN.search(raw):
        source = SOURCE_WEBDL
        if score > 0:
            score = score + 2
    elif HDTV_PATTERN.search(raw):
        source = SOURCE_HDTV
        if score > 0:
            score = score + 1
    elif CAM_PATTERN.search(raw):
        source = SOURCE_CAM
        # não dar bônus; pode até reduzir se quiser rejeitar CAM depois

    return VideoQualityInfo(
        kind=kind,
        score=score,
        resolution_p=resolution_p,
        codec=codec,
        source=source,
        raw_title=raw,
    )


def is_acceptable_video(info: VideoQualityInfo) -> bool:
    """Para vídeo, aceitamos qualquer resultado; a ordenação por score prioriza melhor resolução/codec/fonte."""
    return True


# Aliases para --format em vídeo
VIDEO_FORMAT_ALIASES: dict[str, str] = {
    "4k": "2160p",
    "2160p": "2160p",
    "1080p": "1080p",
    "720p": "720p",
    "x265": "x265",
    "hevc": "x265",
    "x264": "x264",
    "h264": "x264",
    "webdl": SOURCE_WEBDL,
    "web-dl": SOURCE_WEBDL,
    "bluray": SOURCE_BLURAY,
    "blu-ray": SOURCE_BLURAY,
    "hdtv": SOURCE_HDTV,
}
VALID_VIDEO_KINDS: set[str] = {"720p", "1080p", "2160p", "x264", "x265", SOURCE_BLURAY, SOURCE_WEBDL, SOURCE_HDTV}


def parse_format_filter_video(format_str: str | None) -> set[str] | None:
    """
    Converte string do tipo '1080p,720p,x265' em set de kinds para vídeo.
    Retorna None se format_str for None ou vazio (sem subfiltro).
    """
    if not format_str or not format_str.strip():
        return None
    allowed: set[str] = set()
    for part in format_str.strip().lower().split(","):
        part = part.strip()
        if not part:
            continue
        kind = VIDEO_FORMAT_ALIASES.get(part, part)
        if kind in VALID_VIDEO_KINDS:
            allowed.add(kind)
    return allowed if allowed else None


def matches_format_video(info: VideoQualityInfo, allowed_kinds: set[str] | None) -> bool:
    """
    True se o resultado passa no filtro de qualidade de vídeo.
    Se allowed_kinds for None, usa is_acceptable_video (comportamento padrão).
    Senão, exige que pelo menos um dos atributos (kind/resolution, codec, source) esteja em allowed_kinds.
    """
    if not is_acceptable_video(info):
        return False
    if allowed_kinds is None:
        return True
    if info.kind != "unknown" and info.kind in allowed_kinds:
        return True
    if info.codec and info.codec in allowed_kinds:
        return True
    if info.source and info.source in allowed_kinds:
        return True
    return False
