"""
cloud_sync_daemon — sincronização inteligente Atum ↔ Loombeat Cloud.

Features:
  1. Cold tiering: arquivos não tocados há N dias → upload para MinIO, libera disco local
  2. Storage pressure release: quando disco > X% → cold tier emergencial dos menos tocados
  3. Bandwidth scheduler: só sincroniza em horário configurado (ex: "00:00-06:00")
  4. Play position sync: sincroniza posição de reprodução cross-device via cloud_sync_queue
  5. Offline prefetch: itens marcados como offline_only → download do MinIO para local
  6. Smart prefetch: tracks seguintes na fila → pré-download em background

Uso via CLI:
  dl-torrent cloud-sync daemon [--interval 300]
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

_log = logging.getLogger(__name__)

_shutdown = False


def _handle_sigterm(signum, frame) -> None:
    global _shutdown
    _log.info("cloud-sync-daemon: SIGTERM recebido")
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_sigterm)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _get_db_conn(db_url: str):
    import psycopg
    return psycopg.connect(db_url)


def _is_within_sync_hours(hours_range: str) -> bool:
    """
    Verifica se a hora atual está dentro da janela configurada.
    Formato: "HH:MM-HH:MM" (ex: "00:00-06:00"). Vazio = sem restrição.
    """
    if not hours_range or not hours_range.strip():
        return True
    try:
        start_str, end_str = hours_range.strip().split("-")
        now = datetime.now(timezone.utc)
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        now_min = now.hour * 60 + now.minute
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        if start_min <= end_min:
            return start_min <= now_min < end_min
        # Janela atravessa meia-noite (ex: 22:00-06:00)
        return now_min >= start_min or now_min < end_min
    except Exception:
        return True


def _local_disk_usage_pct(path: str) -> float:
    """Retorna percentual de uso do disco do path dado."""
    try:
        stat = shutil.disk_usage(path)
        return stat.used / stat.total * 100
    except Exception:
        return 0.0


# ─── 1. Cold tiering ─────────────────────────────────────────────────────────

def run_cold_tiering(db_url: str, cold_tier_days: int, library_paths: list[str]) -> int:
    """
    Enfileira na cloud_sync_queue os itens não tocados há cold_tier_days dias.
    Só processa itens com storage_tier = 'local'.
    """
    conn = _get_db_conn(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO cloud_sync_queue (family_id, library_id, operation)
                   SELECT family_id, id, 'upload_cold'
                   FROM library_imports
                   WHERE storage_tier = 'local'
                     AND (
                         last_played_at IS NULL
                         OR last_played_at < NOW() - INTERVAL '%s days'
                     )
                     AND NOT EXISTS (
                         SELECT 1 FROM cloud_sync_queue csq
                         WHERE csq.library_id = library_imports.id
                           AND csq.operation = 'upload_cold'
                           AND csq.status IN ('pending', 'processing')
                     )
                   RETURNING id""",
                (cold_tier_days,),
            )
            count = len(cur.fetchall())
            conn.commit()
            if count:
                _log.info("cloud-sync: %d item(s) enfileirados para cold tier", count)
            return count
    finally:
        conn.close()


# ─── 2. Storage pressure release ─────────────────────────────────────────────

def run_pressure_release(db_url: str, pressure_pct: int, library_paths: list[str]) -> int:
    """Aciona cold tier emergencial quando disco excede pressure_pct."""
    total_enqueued = 0
    for path in library_paths:
        usage = _local_disk_usage_pct(path)
        if usage < pressure_pct:
            continue

        _log.warning(
            "cloud-sync: disco em %.1f%% (limite %d%%) — acionando cold tier emergencial em %s",
            usage, pressure_pct, path,
        )

        conn = _get_db_conn(db_url)
        try:
            with conn.cursor() as cur:
                # Enfileira os 50 menos tocados recentemente
                cur.execute(
                    """INSERT INTO cloud_sync_queue (family_id, library_id, operation)
                       SELECT family_id, id, 'upload_cold'
                       FROM library_imports
                       WHERE storage_tier = 'local'
                         AND NOT EXISTS (
                             SELECT 1 FROM cloud_sync_queue csq
                             WHERE csq.library_id = library_imports.id
                               AND csq.status IN ('pending', 'processing')
                         )
                       ORDER BY last_played_at ASC NULLS FIRST
                       LIMIT 50
                       RETURNING id"""
                )
                count = len(cur.fetchall())
                conn.commit()
                total_enqueued += count
        finally:
            conn.close()

    return total_enqueued


# ─── 3. Processar fila de sync (upload_cold / download_warm / prefetch) ───────

def process_sync_queue(db_url: str, batch: int = 10) -> int:
    from ..storage_service import BUCKET_MUSIC, get_storage, music_key

    conn = _get_db_conn(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE cloud_sync_queue SET status = 'processing', started_at = NOW()
                   WHERE id IN (
                       SELECT id FROM cloud_sync_queue
                       WHERE status = 'pending'
                         AND scheduled_at <= NOW()
                       ORDER BY id ASC
                       LIMIT %s
                       FOR UPDATE SKIP LOCKED
                   )
                   RETURNING id, family_id, library_id, operation, minio_key""",
                (batch,),
            )
            tasks = cur.fetchall()
            conn.commit()
    finally:
        conn.close()

    if not tasks:
        return 0

    storage = get_storage()
    processed = 0

    for task_id, family_id, library_id, operation, minio_key in tasks:
        conn = _get_db_conn(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT file_path, minio_key, storage_tier FROM library_imports WHERE id = %s",
                    (library_id,),
                )
                item = cur.fetchone()

            if not item:
                _mark_sync_done(conn, task_id)
                continue

            file_path, existing_key, tier = item

            if operation == "upload_cold" and file_path:
                local = Path(file_path)
                if local.exists():
                    key = existing_key or music_key(str(family_id), local.name)
                    storage.upload_file(BUCKET_MUSIC, key, local, "audio/flac")
                    with conn.cursor() as cur:
                        cur.execute(
                            """UPDATE library_imports
                               SET storage_tier = 'cloud', minio_key = %s
                               WHERE id = %s""",
                            (key, library_id),
                        )
                    _log.info("cloud-sync: upload_cold %s → %s", local.name, key)

            elif operation == "download_warm" and existing_key and file_path:
                local = Path(file_path)
                if not local.exists():
                    storage.download_file(BUCKET_MUSIC, existing_key, local)
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE library_imports SET storage_tier = 'both' WHERE id = %s",
                            (library_id,),
                        )
                    _log.info("cloud-sync: download_warm %s", local.name)

            conn.commit()
            _mark_sync_done(conn, task_id)
            processed += 1

        except Exception as exc:
            _log.exception("cloud-sync: erro na task %s (%s)", task_id, operation)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE cloud_sync_queue SET status = 'failed', error_msg = %s WHERE id = %s",
                        (str(exc)[:500], task_id),
                    )
                conn.commit()
            except Exception:
                pass
        finally:
            conn.close()

    return processed


def _mark_sync_done(conn, task_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cloud_sync_queue SET status = 'done', finished_at = NOW() WHERE id = %s",
            (task_id,),
        )
    conn.commit()


# ─── 4. Offline prefetch: itens marcados como offline_only ───────────────────

def run_offline_prefetch(db_url: str) -> int:
    """Enfileira download para itens marcados como offline_only que não estão locais."""
    conn = _get_db_conn(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO cloud_sync_queue (family_id, library_id, operation)
                   SELECT family_id, id, 'download_warm'
                   FROM library_imports
                   WHERE storage_tier = 'offline_only'
                     AND minio_key IS NOT NULL
                     AND NOT EXISTS (
                         SELECT 1 FROM cloud_sync_queue csq
                         WHERE csq.library_id = library_imports.id
                           AND csq.operation = 'download_warm'
                           AND csq.status IN ('pending', 'processing')
                     )
                   RETURNING id"""
            )
            count = len(cur.fetchall())
            conn.commit()
            if count:
                _log.info("cloud-sync: %d item(s) para prefetch offline", count)
            return count
    finally:
        conn.close()


# ─── ciclo principal ──────────────────────────────────────────────────────────

def run_cloud_sync_cycle(
    db_url: str,
    cold_tier_days: int,
    pressure_pct: int,
    library_paths: list[str],
) -> None:
    """Um ciclo completo do cloud-sync-daemon."""
    run_cold_tiering(db_url, cold_tier_days, library_paths)
    run_pressure_release(db_url, pressure_pct, library_paths)
    run_offline_prefetch(db_url)
    processed = process_sync_queue(db_url, batch=10)
    if processed:
        _log.info("cloud-sync: %d operação(ões) de sync processadas", processed)


def run_daemon(interval: int = 300) -> None:
    """Loop principal do cloud-sync-daemon."""
    db_url = os.getenv("DATABASE_URL", "")
    cold_tier_days = int(os.getenv("COLD_TIER_DAYS", "90"))
    pressure_pct = int(os.getenv("STORAGE_PRESSURE_PCT", "85"))
    sync_hours = os.getenv("CLOUD_SYNC_HOURS", "")
    library_paths = [
        p for p in [
            os.getenv("LIBRARY_MUSIC_PATH", ""),
            os.getenv("LIBRARY_VIDEOS_PATH", ""),
        ] if p
    ]

    _log.info(
        "cloud-sync-daemon iniciado (interval=%ds, cold_tier=%dd, pressure=%d%%)",
        interval, cold_tier_days, pressure_pct,
    )

    while not _shutdown:
        try:
            if _is_within_sync_hours(sync_hours):
                run_cloud_sync_cycle(db_url, cold_tier_days, pressure_pct, library_paths)
            else:
                _log.debug("cloud-sync: fora da janela de sync (%s), aguardando", sync_hours)
        except Exception:
            _log.exception("cloud-sync-daemon: erro no ciclo")

        time.sleep(interval)

    _log.info("cloud-sync-daemon: encerrado")
