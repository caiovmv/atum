"""Serviço HLS: transcodifica vídeos em HLS adaptativo via FFmpeg e gerencia cache de segmentos.

Fluxo:
1. Endpoint /hls/{file_index}/master.m3u8 chama ensure_transcoding()
2. Se não há cache, obtém o caminho do arquivo via Runner (/downloads/{id}/file-path)
3. Inicia FFmpeg em background (asyncio task) — gera 3 variantes (360p, 720p, 1080p)
4. Enquanto processa, retorna 202 Accepted; cliente faz polling via /hls/{file_index}/status
5. Quando pronto, serve master.m3u8 e segmentos via FileResponse

Limitações Phase 1:
- Estado em memória (in-process dict) → não sobrevive a restart de pod
- Sem DRM — segmentos sem criptografia
- Um único pod API; para multi-pod usar Redis para coordenar jobs (Phase 2)
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Literal

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v",
    ".ts", ".flv", ".wmv", ".mpg", ".mpeg",
}

HLSStatus = Literal["processing", "ready", "error"]


class HLSJob:
    """Estado de um job de transcodificação HLS."""

    __slots__ = ("status", "progress", "error")

    def __init__(self) -> None:
        self.status: HLSStatus = "processing"
        self.progress: int = 0
        self.error: str | None = None


# Registro in-memory: {"{library_id}_{file_index}" → HLSJob}
_jobs: dict[str, HLSJob] = {}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _job_key(library_id: int, file_index: int) -> str:
    return f"{library_id}_{file_index}"


def _cache_dir(library_id: int, file_index: int) -> Path:
    return get_settings().hls_cache_path / _job_key(library_id, file_index)


def _runner_url(path: str) -> str:
    base = (get_settings().download_runner_url or "http://localhost:9092").rstrip("/")
    return f"{base}{path}"


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def get_job(library_id: int, file_index: int) -> HLSJob | None:
    """Retorna o job atual (ou None se nunca iniciado)."""
    return _jobs.get(_job_key(library_id, file_index))


def master_manifest_path(library_id: int, file_index: int) -> Path:
    return _cache_dir(library_id, file_index) / "master.m3u8"


def hls_file_path(library_id: int, file_index: int, hls_relative: str) -> Path:
    """Resolve um caminho relativo (ex: stream_0/seg001.ts) dentro do cache do job."""
    return _cache_dir(library_id, file_index) / hls_relative


# Conteúdo do master.m3u8 pré-gerado (antes do FFmpeg iniciar).
# Permite que o Shaka Player comece a carregar imediatamente enquanto os
# segmentos ainda estão sendo gerados — reprodução progressiva "live-like".
_MASTER_M3U8_TEMPLATE = """\
#EXTM3U
#EXT-X-VERSION:3

#EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=640x360,CODECS="avc1.42c01e,mp4a.40.2"
stream_0/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION=1280x720,CODECS="avc1.42c01e,mp4a.40.2"
stream_1/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1920x1080,CODECS="avc1.42c01e,mp4a.40.2"
stream_2/playlist.m3u8
"""


def is_playable(library_id: int, file_index: int) -> bool:
    """True quando há ao menos uma variante com segmentos disponíveis.

    Usado para habilitar reprodução progressiva: o Shaka Player pode carregar
    o manifest assim que o primeiro segmento de qualquer variante estiver pronto
    (~6–12 s após o início do FFmpeg), sem esperar a transcodificação completa.
    """
    cache_dir = _cache_dir(library_id, file_index)
    for v in range(3):
        pl = cache_dir / f"stream_{v}" / "playlist.m3u8"
        # Playlist com >100 bytes tem pelo menos uma entrada #EXTINF (1 segmento)
        if pl.exists() and pl.stat().st_size > 100:
            return True
    return False


async def ensure_transcoding(library_id: int, file_index: int) -> HLSJob:
    """Garante que o job de transcodificação esteja em andamento ou concluído.

    Retorna o HLSJob atual. O chamador deve checar job.status:
    - "processing" → responder 202 Accepted
    - "ready"      → servir master.m3u8
    - "error"      → responder 500
    """
    key = _job_key(library_id, file_index)

    # Job já registrado (processing, ready ou error)
    if key in _jobs:
        return _jobs[key]

    # Cache em disco de runs anteriores sobreviveu ao restart do pod
    if master_manifest_path(library_id, file_index).exists():
        job = HLSJob()
        job.status = "ready"
        job.progress = 100
        _jobs[key] = job
        return job

    # Obtém caminho do arquivo via Runner
    input_path = await _fetch_file_path(library_id, file_index)
    if not input_path:
        job = HLSJob()
        job.status = "error"
        job.error = "Não foi possível resolver o caminho do arquivo via Runner."
        _jobs[key] = job
        return job

    if not _is_video(input_path):
        job = HLSJob()
        job.status = "error"
        job.error = f"Arquivo {input_path.suffix} não é vídeo; HLS não suportado para áudio."
        _jobs[key] = job
        return job

    # Inicia transcodificação em background
    job = HLSJob()
    _jobs[key] = job
    asyncio.create_task(
        _run_ffmpeg(str(input_path), _cache_dir(library_id, file_index), job),
        name=f"hls-{key}",
    )
    logger.info("HLS: job iniciado para library_id=%d file_index=%d", library_id, file_index)
    return job


# ---------------------------------------------------------------------------
# Internos assíncronos
# ---------------------------------------------------------------------------


async def _fetch_file_path(library_id: int, file_index: int) -> Path | None:
    """Consulta o Runner para obter o caminho absoluto do arquivo."""
    url = _runner_url(f"/downloads/{library_id}/file-path?file_index={file_index}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                raw = (data.get("path") or "").strip()
                return Path(raw) if raw else None
            logger.warning("HLS: Runner retornou %d para file-path", r.status_code)
    except Exception:
        logger.exception("HLS: erro ao consultar Runner para file-path")
    return None


async def _run_ffmpeg(input_path: str, cache_dir: Path, job: HLSJob) -> None:
    """Executa FFmpeg em subprocess assíncrono.

    Gera HLS adaptativo com 3 variantes:
    - stream_0: 360p @ 500 kbps
    - stream_1: 720p @ 1500 kbps
    - stream_2: 1080p @ 3000 kbps

    O master.m3u8 é pré-escrito antes do FFmpeg iniciar. Assim que o primeiro
    segmento de qualquer variante estiver pronto (~6 s), o Shaka Player pode
    começar a reproduzir sem esperar a transcodificação completa.
    """
    # Cria diretórios e pré-escreve master.m3u8 ANTES do FFmpeg
    for v in range(3):
        (cache_dir / f"stream_{v}").mkdir(parents=True, exist_ok=True)
    master_file = cache_dir / "master.m3u8"
    if not master_file.exists():
        master_file.write_text(_MASTER_M3U8_TEMPLATE, encoding="utf-8")

    segment_pattern = str(cache_dir / "stream_%v" / "seg%05d.ts")
    playlist_pattern = str(cache_dir / "stream_%v" / "playlist.m3u8")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        # Mapeia o primeiro stream de vídeo e áudio (? = opcional, não falha se ausente)
        "-map", "0:v:0?", "-map", "0:a:0?",
        "-map", "0:v:0?", "-map", "0:a:0?",
        "-map", "0:v:0?", "-map", "0:a:0?",
        # Codec
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-ac", "2",
        # Variant 0: 360p
        "-b:v:0", "500k", "-s:v:0", "640x360",
        # Variant 1: 720p
        "-b:v:1", "1500k", "-s:v:1", "1280x720",
        # Variant 2: 1080p
        "-b:v:2", "3000k", "-s:v:2", "1920x1080",
        "-var_stream_map", "v:0,a:0 v:1,a:1 v:2,a:2",
        # event: playlist cresce incrementalmente; Shaka re-busca até ver #EXT-X-ENDLIST
        "-hls_playlist_type", "event",
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", segment_pattern,
        "-f", "hls",
        playlist_pattern,
    ]

    logger.info("HLS: iniciando FFmpeg → %s", cache_dir)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = (stderr or b"").decode(errors="replace")[-1000:]
            logger.error("HLS: FFmpeg falhou (rc=%d): %s", proc.returncode, err)
            job.status = "error"
            job.error = err
        else:
            # Verifica se master.m3u8 foi gerado
            if Path(master_path).exists():
                job.status = "ready"
                job.progress = 100
                logger.info("HLS: pronto → %s", master_path)
            else:
                job.status = "error"
                job.error = "FFmpeg concluiu mas master.m3u8 não foi gerado."
    except FileNotFoundError:
        job.status = "error"
        job.error = "FFmpeg não encontrado. Instale ffmpeg na imagem."
        logger.error("HLS: ffmpeg não encontrado no PATH")
    except Exception:
        job.status = "error"
        job.error = "Erro inesperado durante transcodificação."
        logger.exception("HLS: erro inesperado no FFmpeg")
