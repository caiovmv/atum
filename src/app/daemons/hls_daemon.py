"""
hls_daemon — daemon de transcodificação HLS isolado da API.

Responsabilidades:
  1. Pollar a tabela hls_jobs para jobs pendentes
  2. Executar FFmpeg para cada job respeitando HLS_MAX_CONCURRENT_JOBS
  3. Fazer upload dos segmentos e playlists para MinIO em tempo real
  4. Atualizar progress_pct e status no banco
  5. Estratégia 'automatic': varrer library_imports e criar jobs para categorias configuradas
  6. Estratégia 'lru': aplicar evicção por tamanho total após cada job concluído

Uso via CLI:
  dl-torrent hls daemon [--interval 10] [--batch 4]

Padrão de implementação: idêntico aos outros daemons (while True + time.sleep).
"""

from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

_shutdown = False


def _handle_sigterm(signum, frame) -> None:
    global _shutdown
    _log.info("hls-daemon: SIGTERM recebido, encerrando após o ciclo atual")
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_sigterm)

# ─── regex para progresso do FFmpeg ──────────────────────────────────────────

_FFMPEG_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")


def _parse_ffmpeg_progress(stderr_line: str) -> float | None:
    m = _FFMPEG_TIME_RE.search(stderr_line)
    if not m:
        return None
    h, mn, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mn * 60 + s


# ─── acesso ao banco ──────────────────────────────────────────────────────────

def _get_db_conn(db_url: str):
    import psycopg
    return psycopg.connect(db_url)


def _fetch_pending_jobs(conn, limit: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE hls_jobs SET status = 'processing', updated_at = NOW()
               WHERE id IN (
                   SELECT id FROM hls_jobs
                   WHERE status = 'pending'
                   ORDER BY created_at ASC
                   LIMIT %s
                   FOR UPDATE SKIP LOCKED
               )
               RETURNING id, family_id, library_id, file_index, strategy""",
            (limit,),
        )
        rows = cur.fetchall()
        conn.commit()
    cols = ["id", "family_id", "library_id", "file_index", "strategy"]
    return [dict(zip(cols, r)) for r in rows]


def _update_job_progress(conn, job_id: str, pct: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE hls_jobs SET progress_pct = %s, updated_at = NOW() WHERE id = %s",
            (min(pct, 99), job_id),
        )
        conn.commit()


def _mark_job_done(conn, job_id: str, minio_prefix: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE hls_jobs
               SET status = 'done', progress_pct = 100, minio_prefix = %s,
                   updated_at = NOW(), last_accessed_at = NOW()
               WHERE id = %s""",
            (minio_prefix, job_id),
        )
        conn.commit()


def _mark_job_failed(conn, job_id: str, error: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE hls_jobs
               SET status = 'failed', error_msg = %s, updated_at = NOW()
               WHERE id = %s""",
            (error[:500], job_id),
        )
        conn.commit()


# ─── resolução do arquivo fonte ───────────────────────────────────────────────

def _resolve_source_file(job: dict, runner_url: str) -> str | None:
    """Consulta o Runner para obter o caminho absoluto do arquivo."""
    import httpx
    try:
        resp = httpx.get(
            f"{runner_url}/downloads/{job['library_id']}/file-path",
            params={"file_index": job["file_index"]},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["path"]
    except Exception as exc:
        _log.warning("hls-daemon: falha ao resolver arquivo para job %s: %s", job["id"], exc)
        return None


def _get_duration(input_path: str) -> float | None:
    """Obtém duração do arquivo via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", input_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        return None


# ─── transcodificação + upload ────────────────────────────────────────────────

def _transcode_and_upload(job: dict, source_path: str, conn) -> None:
    from ..storage_service import BUCKET_HLS, get_storage, hls_prefix

    storage = get_storage()
    prefix = hls_prefix(str(job["family_id"]), job["library_id"], job["file_index"])
    duration = _get_duration(source_path)
    job_id = str(job["id"])

    with tempfile.TemporaryDirectory(prefix="hls_") as tmpdir:
        tmp = Path(tmpdir)
        master_m3u8 = tmp / "master.m3u8"
        stream_dir = tmp / "stream_0"
        stream_dir.mkdir()

        # Comanda FFmpeg — variante única por simplicidade (daemon pode expandir para multi-bitrate)
        cmd = [
            "ffmpeg", "-y",
            "-i", source_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-f", "hls",
            "-hls_time", "6",
            "-hls_list_size", "0",
            "-hls_playlist_type", "event",
            "-hls_segment_filename", str(stream_dir / "seg_%05d.ts"),
            str(stream_dir / "stream.m3u8"),
        ]

        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, bufsize=1)

        if proc.stderr is None:
            raise RuntimeError("FFmpeg não abriu pipe de stderr")

        segments_uploaded: set[str] = set()

        for line in proc.stderr:
            # Progresso
            elapsed = _parse_ffmpeg_progress(line)
            if elapsed is not None and duration and duration > 0:
                pct = int(min(elapsed / duration * 100, 99))
                _update_job_progress(conn, job_id, pct)

            # Upload incremental de segmentos prontos
            for seg in sorted(stream_dir.glob("seg_*.ts")):
                seg_key = f"{prefix}{seg.name}"
                if seg_key not in segments_uploaded:
                    try:
                        storage.upload_file(BUCKET_HLS, seg_key, seg, "video/MP2T")
                        segments_uploaded.add(seg_key)
                    except Exception as e:
                        _log.debug("hls-daemon: falha ao fazer upload de %s: %s", seg.name, e)

        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg saiu com código {proc.returncode}")

        # Upload das playlists finais
        if (stream_dir / "stream.m3u8").exists():
            storage.upload_file(BUCKET_HLS, f"{prefix}stream_0/stream.m3u8",
                                stream_dir / "stream.m3u8", "application/vnd.apple.mpegurl")

        # Gera e faz upload do master.m3u8
        master_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
        master_content += "#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION=1280x720\n"
        master_content += "stream_0/stream.m3u8\n"
        master_m3u8.write_text(master_content)
        storage.upload_file(BUCKET_HLS, f"{prefix}master.m3u8",
                            master_m3u8, "application/vnd.apple.mpegurl")

        # Upload de qualquer segmento que ficou para trás
        for seg in stream_dir.glob("seg_*.ts"):
            seg_key = f"{prefix}{seg.name}"
            if seg_key not in segments_uploaded:
                storage.upload_file(BUCKET_HLS, seg_key, seg, "video/MP2T")

    _mark_job_done(conn, job_id, f"s3://{BUCKET_HLS}/{prefix}")
    _log.info("hls-daemon: job %s concluído → %s", job_id, prefix)


def _process_job(job: dict, runner_url: str, db_url: str) -> None:
    """Processa um job HLS em thread separada (cada thread tem sua própria conexão)."""
    conn = _get_db_conn(db_url)
    try:
        source = _resolve_source_file(job, runner_url)
        if not source:
            _mark_job_failed(conn, str(job["id"]), "Arquivo fonte não encontrado")
            return

        _transcode_and_upload(job, source, conn)
    except Exception as exc:
        _log.exception("hls-daemon: erro no job %s", job["id"])
        try:
            _mark_job_failed(conn, str(job["id"]), str(exc))
        except Exception:
            pass
    finally:
        conn.close()


# ─── estratégia automatic: cria jobs para toda a biblioteca ─────────────────

def _create_automatic_jobs(db_url: str, categories: list[str]) -> int:
    """Insere jobs HLS para itens da biblioteca sem job existente."""
    if not categories:
        return 0

    content_type_map = {
        "audio": ("music", "concerts"),
        "video": ("movies",),
        "tv": ("tv",),
        "concerts": ("concerts",),
    }
    content_types: list[str] = []
    for cat in categories:
        content_types.extend(content_type_map.get(cat, []))

    if not content_types:
        return 0

    conn = _get_db_conn(db_url)
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(content_types))
            cur.execute(
                f"""INSERT INTO hls_jobs (family_id, library_id, file_index, strategy)
                    SELECT DISTINCT li.family_id, li.id, 0, 'automatic'
                    FROM library_imports li
                    WHERE li.content_type IN ({placeholders})
                      AND li.storage_tier IN ('local', 'both')
                      AND NOT EXISTS (
                          SELECT 1 FROM hls_jobs hj
                          WHERE hj.family_id = li.family_id
                            AND hj.library_id = li.id
                            AND hj.file_index = 0
                      )
                    ON CONFLICT (family_id, library_id, file_index) DO NOTHING
                    RETURNING id""",
                content_types,
            )
            inserted = len(cur.fetchall())
            conn.commit()
            if inserted:
                _log.info("hls-daemon: estratégia automatic criou %d jobs", inserted)
            return inserted
    finally:
        conn.close()


# ─── evicção LRU ─────────────────────────────────────────────────────────────

def _evict_lru_if_needed(db_url: str, max_size_gb: float) -> None:
    """Remove os jobs HLS mais antigos por acesso se o total exceder max_size_gb."""
    from ..storage_service import BUCKET_HLS, get_storage
    storage = get_storage()
    total_bytes = storage.bucket_size_bytes(BUCKET_HLS)
    max_bytes = int(max_size_gb * 1024**3)
    if total_bytes <= max_bytes:
        return

    _log.info(
        "hls-daemon: LRU evicção — uso atual %.1f GB > limite %.1f GB",
        total_bytes / 1024**3, max_size_gb,
    )

    conn = _get_db_conn(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, minio_prefix FROM hls_jobs
                   WHERE status = 'done' AND strategy = 'lru'
                   ORDER BY last_accessed_at ASC
                   LIMIT 20"""
            )
            candidates = cur.fetchall()

        for job_id, prefix in candidates:
            if not prefix:
                continue
            # Remove objetos do MinIO
            bucket = BUCKET_HLS
            key_prefix = prefix.replace(f"s3://{bucket}/", "")
            keys = storage.list_objects(bucket, key_prefix)
            for key in keys:
                try:
                    storage.delete(bucket, key)
                except Exception:
                    pass

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE hls_jobs SET status = 'evicted', minio_prefix = NULL WHERE id = %s",
                    (job_id,),
                )
            conn.commit()

            # Verifica se já está abaixo do limite
            total_bytes = storage.bucket_size_bytes(BUCKET_HLS)
            if total_bytes <= max_bytes:
                break
    finally:
        conn.close()


# ─── ciclo principal ──────────────────────────────────────────────────────────

def run_hls_cycle(
    db_url: str,
    runner_url: str,
    batch: int = 4,
    max_workers: int = 2,
    hls_lru_max_gb: float = 100.0,
) -> int:
    """Executa um ciclo do daemon HLS. Retorna número de jobs processados."""
    conn = _get_db_conn(db_url)
    try:
        jobs = _fetch_pending_jobs(conn, batch)
    finally:
        conn.close()

    if not jobs:
        return 0

    _log.info("hls-daemon: processando %d job(s)", len(jobs))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_process_job, job, runner_url, db_url): job
            for job in jobs
        }
        for fut in as_completed(futures):
            exc = fut.exception()
            if exc:
                _log.error("hls-daemon: job falhou com exceção: %s", exc)

    # Estratégia LRU: verificar evicção após cada ciclo
    try:
        _evict_lru_if_needed(db_url, hls_lru_max_gb)
    except Exception:
        _log.exception("hls-daemon: erro na evicção LRU")

    return len(jobs)


# ─── ponto de entrada do daemon ───────────────────────────────────────────────

def run_daemon(interval: int = 10, batch: int = 4) -> None:
    """Loop principal do hls-daemon."""
    db_url = os.getenv("DATABASE_URL", "")
    runner_url = os.getenv("DOWNLOAD_RUNNER_URL", "http://runner:9092")
    max_workers = int(os.getenv("HLS_MAX_CONCURRENT_JOBS", "2"))

    # Configurações de estratégia lidas do banco (via app_settings)
    hls_lru_max_gb = float(os.getenv("HLS_LRU_MAX_GB", "100"))

    auto_categories_raw = os.getenv("HLS_AUTO_CATEGORIES", "")
    auto_categories = [c.strip() for c in auto_categories_raw.split(",") if c.strip()]
    hls_strategy = os.getenv("HLS_STRATEGY", "on_demand")

    _log.info(
        "hls-daemon iniciado (strategy=%s, interval=%ds, batch=%d, workers=%d)",
        hls_strategy, interval, batch, max_workers,
    )

    while not _shutdown:
        try:
            if hls_strategy == "automatic" and auto_categories:
                _create_automatic_jobs(db_url, auto_categories)

            processed = run_hls_cycle(
                db_url=db_url,
                runner_url=runner_url,
                batch=batch,
                max_workers=max_workers,
                hls_lru_max_gb=hls_lru_max_gb,
            )
            if processed:
                _log.info("hls-daemon: ciclo concluiu %d job(s)", processed)
        except Exception:
            _log.exception("hls-daemon: erro no ciclo principal")

        time.sleep(interval)

    _log.info("hls-daemon: encerrado")
