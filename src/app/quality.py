"""Parser de formato/bitrate no título do torrent e score de qualidade."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Literal

# Bitrate mínimo aceitável para MP3 (kbps). Abaixo disso (ex.: 128) rejeitamos.
MP3_MIN_ACCEPTABLE_KBPS = 198

# Score para ordenação (maior = melhor)
class QualityScore(IntEnum):
    UNKNOWN = 0
    MP3_ACCEPTABLE = 1   # MP3 até 198 kbps (V0, 192, 256, etc.)
    MP3_320 = 2
    ALAC = 3
    FLAC = 4


QualityType = Literal["flac", "alac", "mp3_320", "mp3_acceptable", "unknown"]


@dataclass
class QualityInfo:
    """Resultado do parser de qualidade a partir do título."""

    kind: QualityType
    score: int
    bitrate_kbps: int | None  # para MP3, quando detectável
    raw_title: str

    @property
    def label(self) -> str:
        if self.kind == "flac":
            return "FLAC"
        if self.kind == "alac":
            return "ALAC"
        if self.kind == "mp3_320":
            return "MP3 320"
        if self.kind == "mp3_acceptable" and self.bitrate_kbps:
            return f"MP3 {self.bitrate_kbps}"
        if self.kind == "mp3_acceptable":
            return "MP3 (≤198)"
        return "?"


# Padrões para detecção (case-insensitive)
FLAC_PATTERN = re.compile(r"\bflac\b", re.I)
ALAC_PATTERN = re.compile(r"\balac\b", re.I)
# MP3 320: 320, 320k, 320kbps, CBR 320
MP3_320_PATTERN = re.compile(r"\b320\s*(?:k(?:bps)?)?\b|\bcbr\s*320\b", re.I)
# V0 = VBR ~245 kbps, aceitável
V0_PATTERN = re.compile(r"\bv0\b|\bvbr\s*v0\b", re.I)
# Bitrate numérico: 192, 256, 198, 224, etc. (evitar 128, 96, 64)
MP3_BITRATE_PATTERN = re.compile(
    r"\b(?:mp3\s*)?(?:(\d{3})\s*(?:k(?:bps)?)?|(\d{3})\s*kbps)\b",
    re.I,
)
# Apenas número seguido de k/kbps (comum em nomes)
BARE_BITRATE_PATTERN = re.compile(r"\b(1[6-9][0-9]|2[0-5][0-9]|320)\s*(?:k(?:bps)?)?\b", re.I)


def parse_quality(title: str) -> QualityInfo:
    """
    Analisa o título do torrent e retorna tipo de qualidade, score e bitrate (se MP3).
    Ordem de preferência: FLAC > ALAC > MP3 320 > MP3 até 198 kbps.
    """
    raw = title.strip()
    if not raw:
        return QualityInfo(kind="unknown", score=QualityScore.UNKNOWN, bitrate_kbps=None, raw_title=raw)

    # Lossless primeiro
    if FLAC_PATTERN.search(raw):
        return QualityInfo(kind="flac", score=QualityScore.FLAC, bitrate_kbps=None, raw_title=raw)
    if ALAC_PATTERN.search(raw):
        return QualityInfo(kind="alac", score=QualityScore.ALAC, bitrate_kbps=None, raw_title=raw)

    # MP3
    if MP3_320_PATTERN.search(raw):
        return QualityInfo(kind="mp3_320", score=QualityScore.MP3_320, bitrate_kbps=320, raw_title=raw)

    # V0 considerado aceitável (VBR ~245)
    if V0_PATTERN.search(raw):
        return QualityInfo(kind="mp3_acceptable", score=QualityScore.MP3_ACCEPTABLE, bitrate_kbps=245, raw_title=raw)

    # Tentar extrair bitrate numérico (320, 256, 198, 192, etc.). Aceitamos só >= 198.
    for m in MP3_BITRATE_PATTERN.finditer(raw):
        k = int(m.group(1) or m.group(2) or 0)
        if k == 320:
            return QualityInfo(kind="mp3_320", score=QualityScore.MP3_320, bitrate_kbps=320, raw_title=raw)
        if MP3_MIN_ACCEPTABLE_KBPS <= k < 320:
            return QualityInfo(kind="mp3_acceptable", score=QualityScore.MP3_ACCEPTABLE, bitrate_kbps=k, raw_title=raw)
        if k < MP3_MIN_ACCEPTABLE_KBPS:
            break

    for m in BARE_BITRATE_PATTERN.finditer(raw):
        k = int(m.group(1))
        if k == 320:
            return QualityInfo(kind="mp3_320", score=QualityScore.MP3_320, bitrate_kbps=320, raw_title=raw)
        if MP3_MIN_ACCEPTABLE_KBPS <= k < 320:
            return QualityInfo(kind="mp3_acceptable", score=QualityScore.MP3_ACCEPTABLE, bitrate_kbps=k, raw_title=raw)

    # Se tem "MP3" no título mas não detectamos bitrate, considerar aceitável (muitos usam "MP3" genérico)
    if re.search(r"\bmp3\b", raw, re.I):
        return QualityInfo(kind="mp3_acceptable", score=QualityScore.MP3_ACCEPTABLE, bitrate_kbps=None, raw_title=raw)

    return QualityInfo(kind="unknown", score=QualityScore.UNKNOWN, bitrate_kbps=None, raw_title=raw)


def is_acceptable(info: QualityInfo) -> bool:
    """Retorna True se a qualidade for pelo menos MP3 até 198 kbps ou melhor."""
    return info.score >= QualityScore.MP3_ACCEPTABLE


# Aliases para --format (subfiltro opcional)
FORMAT_ALIASES: dict[str, str] = {
    "320": "mp3_320",
    "192": "mp3_acceptable",
    "mp3": "mp3_acceptable",
}
VALID_KINDS: set[str] = {"flac", "alac", "mp3_320", "mp3_acceptable"}


def parse_format_filter(format_str: str | None) -> set[str] | None:
    """
    Converte string do tipo 'flac,alac,320' em set de kinds.
    Retorna None se format_str for None ou vazio (sem subfiltro).
    """
    if not format_str or not format_str.strip():
        return None
    allowed: set[str] = set()
    for part in format_str.strip().lower().split(","):
        part = part.strip()
        if not part:
            continue
        kind = FORMAT_ALIASES.get(part, part)
        if kind in VALID_KINDS:
            allowed.add(kind)
    return allowed if allowed else None


def matches_format(info: QualityInfo, allowed_kinds: set[str] | None) -> bool:
    """
    True se o resultado passa no filtro de qualidade.
    Se allowed_kinds for None, usa is_acceptable (comportamento padrão).
    Senão, exige que info.kind esteja em allowed_kinds (e continua aceitável).
    """
    if not is_acceptable(info):
        return False
    if allowed_kinds is None:
        return True
    return info.kind in allowed_kinds
