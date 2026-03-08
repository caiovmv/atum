"""Comparação de qualidade para decidir se uma versão substitui outra na biblioteca."""

from __future__ import annotations

VIDEO_QUALITY_ORDER = ["480p", "720p", "1080p", "2160p"]
MUSIC_QUALITY_ORDER = ["128", "192", "256", "V2", "V0", "320", "FLAC"]


def video_quality_rank(label: str | None) -> int:
    """Retorna rank numérico da qualidade de vídeo (maior = melhor). -1 se desconhecida."""
    if not label:
        return -1
    normalized = label.strip().lower()
    for i, q in enumerate(VIDEO_QUALITY_ORDER):
        if q.lower() == normalized:
            return i
    if "4k" in normalized or "uhd" in normalized:
        return VIDEO_QUALITY_ORDER.index("2160p")
    return -1


def music_quality_rank(label: str | None) -> int:
    """Retorna rank numérico da qualidade de música (maior = melhor). -1 se desconhecida."""
    if not label:
        return -1
    normalized = label.strip().upper()
    for i, q in enumerate(MUSIC_QUALITY_ORDER):
        if q.upper() == normalized:
            return i
    if "LOSSLESS" in normalized:
        return MUSIC_QUALITY_ORDER.index("FLAC")
    return -1


def is_upgrade(
    new_quality: str | None,
    existing_quality: str | None,
    content_type: str,
) -> bool:
    """
    Retorna True se new_quality é superior a existing_quality.
    Para vídeos: compara resolução. Para música: compara formato/bitrate.
    """
    if content_type in ("movies", "tv"):
        new_rank = video_quality_rank(new_quality)
        old_rank = video_quality_rank(existing_quality)
    elif content_type == "music":
        new_rank = music_quality_rank(new_quality)
        old_rank = music_quality_rank(existing_quality)
    else:
        return False

    if new_rank < 0:
        return False
    if old_rank < 0:
        return True
    return new_rank > old_rank
