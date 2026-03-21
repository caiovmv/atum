"""Serviço HLS: transcodifica vídeos em HLS adaptativo via FFmpeg e gerencia cache de segmentos.

Fluxo:
1. Endpoint /hls/{file_index}/master.m3u8 chama ensure_transcoding()
2. Se não há cache, obtém o caminho do arquivo via Runner (/downloads/{id}/file-path)
3. Detecta resolução e duração do vídeo via ffprobe
4. Seleciona variantes HLS compatíveis com a resolução original (sem upscale)
5. Inicia FFmpeg em background (asyncio task) — até 3 variantes (360p, 720p, 1080p)
6. Enquanto processa, retorna 202 Accepted; cliente faz polling via /hls/{file_index}/status
7. Quando pronto, serve master.m3u8 e segmentos via FileResponse

Limitações Phase 1:
- Estado em memória (in-process dict) → não sobrevive a restart de pod
- Sem DRM — segmentos sem criptografia
- Um único pod API; para multi-pod usar Redis para coordenar jobs (Phase 2)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import time
from dataclasses import dataclass
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

# Regex para extrair timestamp de progresso do stderr do FFmpeg:
# "frame=  100 fps= 30 ... time=00:01:23.45 ..."
_FFMPEG_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")


# ---------------------------------------------------------------------------
# Modelos de dados
# ---------------------------------------------------------------------------


@dataclass
class VideoInfo:
    """Informações de vídeo extraídas via ffprobe."""

    duration: float | None
    width: int
    height: int


@dataclass
class _Variant:
    """Configuração de uma variante HLS."""

    name: str
    height: int
    width: int
    bandwidth: int
    bitrate: str


# Variantes disponíveis, da menor para a maior resolução.
# Apenas variantes com height <= resolução original são selecionadas.
_ALL_VARIANTS: list[_Variant] = [
    _Variant("360p",  360,  640,   500_000, "500k"),
    _Variant("720p",  720, 1280, 1_500_000, "1500k"),
    _Variant("1080p", 1080, 1920, 3_000_000, "3000k"),
]


def _select_variants(source_height: int) -> list[_Variant]:
    """Seleciona variantes com altura ≤ resolução original.

    Garante sempre ao menos uma variante, mesmo que o vídeo seja abaixo de 360p.
    Evita upscale inútil que desperdiça CPU e espaço em disco.
    """
    selected = [v for v in _ALL_VARIANTS if v.height <= source_height]
    return selected if selected else [_ALL_VARIANTS[0]]


def _build_master_m3u8(variants: list[_Variant]) -> str:
    """Gera o conteúdo do master.m3u8 com base nas variantes selecionadas."""
    lines = ["#EXTM3U", "#EXT-X-VERSION:3", ""]
    for i, v in enumerate(variants):
        lines.append(
            f'#EXT-X-STREAM-INF:BANDWIDTH={v.bandwidth},'
            f'RESOLUTION={v.width}x{v.height},'
            f'CODECS="avc1.42c01e,mp4a.40.2"'
        )
        lines.append(f"stream_{i}/playlist.m3u8")
    return "\n".join(lines) + "\n"


def _build_ffmpeg_cmd(input_path: str, cache_dir: Path, variants: list[_Variant]) -> list[str]:
    """Constrói o comando FFmpeg para HLS adaptativo com múltiplas variantes."""
    n = len(variants)
    cmd = ["ffmpeg", "-y", "-i", input_path]

    # Mapeia vídeo e áudio para cada variante (? = opcional se ausente no fonte)
    for _ in range(n):
        cmd += ["-map", "0:v:0?", "-map", "0:a:0?"]

    cmd += ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-ac", "2"]

    for i, v in enumerate(variants):
        cmd += [f"-b:v:{i}", v.bitrate, f"-s:v:{i}", f"{v.width}x{v.height}"]

    var_stream_map = " ".join(f"v:{i},a:{i}" for i in range(n))

    cmd += [
        "-var_stream_map", var_stream_map,
        # event: playlist cresce incrementalmente; Shaka re-busca até ver #EXT-X-ENDLIST
        "-hls_playlist_type", "event",
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", str(cache_dir / "stream_%v" / "seg%05d.ts"),
        "-f", "hls",
        str(cache_dir / "stream_%v" / "playlist.m3u8"),
    ]
    return cmd


# ---------------------------------------------------------------------------
# Estado de jobs
# ---------------------------------------------------------------------------


class HLSJob:
    """Estado de um job de transcodificação HLS."""

    __slots__ = ("status", "progress", "error")

    def __init__(self) -> None:
        self.status: HLSStatus = "processing"
        self.progress: int = 0
        self.error: str | None = None


# Registro in-memory: {"{library_id}_{file_index}" → HLSJob}
_jobs: dict[str, HLSJob] = {}

# Semáforo para limitar jobs FFmpeg em paralelo. Criado na primeira chamada
# (dentro do event loop do FastAPI) para evitar problemas de loop incorreto.
_ffmpeg_semaphore: asyncio.Semaphore | None = None


def _get_ffmpeg_semaphore() -> asyncio.Semaphore:
    """Retorna o semáforo de concorrência FFmpeg, criando-o na primeira chamada."""
    global _ffmpeg_semaphore
    if _ffmpeg_semaphore is None:
        limit = max(1, get_settings().hls_max_concurrent_jobs)
        _ffmpeg_semaphore = asyncio.Semaphore(limit)
        logger.info("HLS: semáforo FFmpeg inicializado com limite=%d", limit)
    return _ffmpeg_semaphore


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


def _safe_read(path: Path) -> str:
    """Lê um arquivo texto silenciando erros de I/O."""
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def get_job(library_id: int, file_index: int) -> HLSJob | None:
    """Retorna o job atual (ou None se nunca iniciado)."""
    return _jobs.get(_job_key(library_id, file_index))


def get_active_job_count() -> int:
    """Retorna a quantidade de jobs FFmpeg atualmente em processamento."""
    return sum(1 for j in _jobs.values() if j.status == "processing")


def master_manifest_path(library_id: int, file_index: int) -> Path:
    return _cache_dir(library_id, file_index) / "master.m3u8"


def hls_file_path(library_id: int, file_index: int, hls_relative: str) -> Path:
    """Resolve um caminho relativo (ex: stream_0/seg001.ts) dentro do cache do job."""
    return _cache_dir(library_id, file_index) / hls_relative


def is_playable(library_id: int, file_index: int) -> bool:
    """True quando há ao menos uma variante com segmentos disponíveis.

    Usado para habilitar reprodução progressiva: o Shaka Player pode carregar
    o manifest assim que o primeiro segmento de qualquer variante estiver pronto
    (~6–12 s após o início do FFmpeg), sem esperar a transcodificação completa.
    """
    cache_dir = _cache_dir(library_id, file_index)
    for variant_dir in cache_dir.glob("stream_*"):
        pl = variant_dir / "playlist.m3u8"
        # Playlist com >100 bytes tem pelo menos uma entrada #EXTINF (1 segmento)
        if pl.exists() and pl.stat().st_size > 100:
            return True
    return False


def invalidate_cache(library_id: int, file_index: int) -> bool:
    """Remove o cache HLS de um arquivo específico e limpa o estado em memória.

    Retorna True se havia cache (foi removido), False se não havia nada.
    Após a invalidação, a próxima requisição ao master.m3u8 re-transcodifica.
    """
    key = _job_key(library_id, file_index)
    had_cache = key in _jobs or master_manifest_path(library_id, file_index).exists()
    _jobs.pop(key, None)
    cache_dir = _cache_dir(library_id, file_index)
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
    return had_cache


def invalidate_all_for_item(library_id: int) -> int:
    """Remove todo o cache HLS de um item da biblioteca (todos os file_index).

    Retorna a quantidade de caches removidos.
    """
    cache_base = get_settings().hls_cache_path
    if not cache_base.exists():
        return 0
    removed = 0
    prefix = f"{library_id}_"
    for d in list(cache_base.iterdir()):
        if not d.is_dir() or not d.name.startswith(prefix):
            continue
        suffix = d.name[len(prefix):]
        if not suffix.isdigit():
            continue
        _jobs.pop(d.name, None)
        shutil.rmtree(d, ignore_errors=True)
        removed += 1
    return removed


def cleanup_partial_caches() -> int:
    """Remove caches HLS incompletos (transcodificações interrompidas por restart do pod).

    Uma transcodificação é considerada completa quando ao menos uma das playlists
    de variante contém `#EXT-X-ENDLIST`. Sem essa marcação, os segmentos ficaram
    parciais e não podem ser reproduzidos integralmente.

    Chamado no lifespan da API para garantir estado limpo após restart.
    Retorna a quantidade de caches removidos.
    """
    cache_base = get_settings().hls_cache_path
    if not cache_base.exists():
        return 0
    removed = 0
    for job_dir in list(cache_base.iterdir()):
        if not job_dir.is_dir():
            continue
        is_complete = any(
            "#EXT-X-ENDLIST" in _safe_read(pl)
            for pl in job_dir.glob("stream_*/playlist.m3u8")
        )
        if not is_complete:
            logger.info("HLS startup cleanup: removendo cache parcial '%s'", job_dir.name)
            shutil.rmtree(job_dir, ignore_errors=True)
            removed += 1
    if removed:
        logger.info("HLS startup cleanup: %d cache(s) parcial(is) removido(s)", removed)
    return removed


def evict_caches(max_age_days: int = 30, max_size_gb: float = 100.0) -> dict:
    """Remove caches HLS antigos ou quando o volume excede o limite de tamanho.

    Política de evicção (ambas condições são avaliadas):
    - Caches com último acesso > max_age_days são sempre removidos.
    - Se tamanho total > max_size_gb, os caches mais antigos são removidos até
      ficar abaixo do limite.

    Jobs atualmente em processamento (status="processing") nunca são removidos
    para não interromper transcodificações em andamento.

    Retorna dict com: evicted (contagem), freed_bytes, freed_mb.
    """
    cache_base = get_settings().hls_cache_path
    if not cache_base.exists():
        return {"evicted": 0, "freed_bytes": 0, "freed_mb": 0}

    # Nunca remover caches de jobs que ainda estão processando
    active_keys = {k for k, j in _jobs.items() if j.status == "processing"}

    now = time.time()
    max_age_secs = max_age_days * 86400
    max_size_bytes = int(max_size_gb * 1024 ** 3)

    dirs: list[tuple[Path, int, float]] = []
    for d in cache_base.iterdir():
        if not d.is_dir() or d.name in active_keys:
            continue
        files = list(d.rglob("*"))
        size = sum(f.stat().st_size for f in files if f.is_file())
        mtimes = [f.stat().st_mtime for f in files if f.is_file()]
        last_mtime = max(mtimes) if mtimes else d.stat().st_mtime
        dirs.append((d, size, last_mtime))

    total_size = sum(s for _, s, _ in dirs)
    dirs.sort(key=lambda x: x[2])  # mais antigos primeiro

    evicted = 0
    freed_bytes = 0
    for d, size, last_mtime in dirs:
        age_secs = now - last_mtime
        if age_secs > max_age_secs or total_size > max_size_bytes:
            _jobs.pop(d.name, None)
            shutil.rmtree(d, ignore_errors=True)
            total_size -= size
            freed_bytes += size
            evicted += 1

    freed_mb = freed_bytes // (1024 * 1024)
    logger.info("HLS eviction: %d cache(s) removido(s), %d MB liberados", evicted, freed_mb)

    # Limpa entradas in-memory cujo cache em disco não existe mais
    # (jobs com status="error" nunca criam cache → acumulam sem nunca serem eviccionados)
    orphans = 0
    for key in list(_jobs.keys()):
        if _jobs[key].status == "processing":
            continue  # não remover jobs ativos
        if not (cache_base / key).exists():
            _jobs.pop(key, None)
            orphans += 1
    if orphans:
        logger.info("HLS eviction: %d entrada(s) órfã(s) removida(s) do dict", orphans)

    return {"evicted": evicted, "freed_bytes": freed_bytes, "freed_mb": freed_mb, "orphans_cleaned": orphans}


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


async def _get_video_info(input_path: str) -> VideoInfo:
    """Retorna duração e resolução do vídeo via ffprobe. Usa defaults seguros se falhar."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-select_streams", "v:0",
        input_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            data = json.loads(stdout.decode(errors="replace"))
            duration_raw = data.get("format", {}).get("duration")
            duration = float(duration_raw) if duration_raw else None
            streams = data.get("streams", [])
            if streams:
                return VideoInfo(
                    duration=duration,
                    width=int(streams[0].get("width") or 0),
                    height=int(streams[0].get("height") or 0),
                )
            return VideoInfo(duration=duration, width=0, height=0)
    except Exception:
        logger.debug("ffprobe: não foi possível obter info de '%s'", input_path)
    return VideoInfo(duration=None, width=0, height=0)


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
    """Executa FFmpeg em subprocess assíncrono com variantes adaptadas à resolução original.

    Detecta a resolução do vídeo fonte via ffprobe e seleciona apenas variantes
    com resolução <= fonte, evitando upscale inútil. O master.m3u8 é pré-escrito
    antes do FFmpeg iniciar para habilitar reprodução progressiva (~6 s de latência).

    Respeita o semáforo de concorrência (HLS_MAX_CONCURRENT_JOBS): se o limite
    já foi atingido, o job aguarda em fila mantendo status="processing" — o spinner
    continua visível para o usuário sem nenhuma mudança na API.
    """
    async with _get_ffmpeg_semaphore():
        await _run_ffmpeg_inner(input_path, cache_dir, job)


async def _run_ffmpeg_inner(input_path: str, cache_dir: Path, job: HLSJob) -> None:
    """Corpo real do FFmpeg — executado sob o semáforo de concorrência."""
    # Detecta resolução e duração para selecionar variantes adequadas
    info = await _get_video_info(input_path)
    source_height = info.height if info.height > 0 else 1080
    variants = _select_variants(source_height)

    logger.info(
        "HLS: %s → %d variante(s): %s (fonte: %dx%d, duração: %.1fs)",
        cache_dir.name,
        len(variants),
        [v.name for v in variants],
        info.width,
        info.height,
        info.duration or 0,
    )

    # Cria diretórios e pré-escreve master.m3u8 ANTES do FFmpeg
    for i in range(len(variants)):
        (cache_dir / f"stream_{i}").mkdir(parents=True, exist_ok=True)
    master_file = cache_dir / "master.m3u8"
    if not master_file.exists():
        master_file.write_text(_build_master_m3u8(variants), encoding="utf-8")

    cmd = _build_ffmpeg_cmd(input_path, cache_dir, variants)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        if proc.stderr is None:
            raise RuntimeError("Falha ao criar pipe de stderr para FFmpeg.")

        # Lê stderr do FFmpeg em chunks e extrai progresso do timestamp `time=`
        # FFmpeg escreve `\r` (sem newline) para sobrescrever a linha de progresso.
        stderr_tail: list[bytes] = []
        buf = b""
        while True:
            chunk = await proc.stderr.read(512)
            if not chunk:
                break
            buf += chunk
            # Processa cada "linha" separada por \r ou \n
            parts = re.split(rb"[\r\n]", buf)
            buf = parts[-1]  # mantém fragmento incompleto no buffer
            for part in parts[:-1]:
                text = part.decode(errors="replace")
                stderr_tail.append(part[-200:])
                m = _FFMPEG_TIME_RE.search(text)
                if m and info.duration and info.duration > 0:
                    h, mn, s = m.groups()
                    current = int(h) * 3600 + int(mn) * 60 + float(s)
                    job.progress = min(99, int(current / info.duration * 100))

        await proc.wait()
        last_stderr = b"".join(stderr_tail[-20:]).decode(errors="replace")

        if proc.returncode != 0:
            logger.error("HLS: FFmpeg falhou (rc=%d): %s", proc.returncode, last_stderr[-500:])
            job.status = "error"
            job.error = last_stderr[-500:] or f"FFmpeg saiu com código {proc.returncode}"
        else:
            job.status = "ready"
            job.progress = 100
            logger.info("HLS: pronto → %s", cache_dir)
    except FileNotFoundError:
        job.status = "error"
        job.error = "FFmpeg não encontrado. Instale ffmpeg na imagem."
        logger.error("HLS: ffmpeg não encontrado no PATH")
    except Exception:
        job.status = "error"
        job.error = "Erro inesperado durante transcodificação."
        logger.exception("HLS: erro inesperado no FFmpeg")
