"""Admin: visão geral de armazenamento."""

from fastapi import APIRouter, Depends, Query

from ...auth_service import AuthUser, require_financial

router = APIRouter(prefix="/storage")


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("/overview")
async def storage_overview(
    actor: AuthUser = Depends(require_financial),
) -> dict:
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT
                     COUNT(*) FILTER (WHERE storage_tier = 'local') AS local_count,
                     COUNT(*) FILTER (WHERE storage_tier = 'cloud') AS cloud_count,
                     COALESCE(SUM(local_size_bytes) FILTER (WHERE storage_tier = 'local'), 0) AS local_bytes,
                     COALESCE(SUM(local_size_bytes) FILTER (WHERE storage_tier = 'cloud'), 0) AS cloud_bytes
                   FROM library_imports"""
            )
            storage_row = await cur.fetchone()

            await cur.execute(
                """SELECT status, COUNT(*) FROM hls_jobs GROUP BY status"""
            )
            hls_rows = await cur.fetchall()

            await cur.execute(
                """SELECT operation, COUNT(*), SUM(size_bytes)
                   FROM cloud_sync_queue
                   GROUP BY operation"""
            )
            sync_rows = await cur.fetchall()

    hls_by_status = {r[0]: r[1] for r in hls_rows}
    sync_by_op = {r[0]: {"count": r[1], "size_bytes": r[2]} for r in sync_rows}

    return {
        "library": {
            "local_count": storage_row[0],
            "cloud_count": storage_row[1],
            "local_bytes": storage_row[2],
            "cloud_bytes": storage_row[3],
        },
        "hls_jobs": hls_by_status,
        "cloud_sync_queue": sync_by_op,
    }


@router.get("/hls-jobs")
async def list_hls_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    job_status: str | None = Query(None),
    actor: AuthUser = Depends(require_financial),
) -> dict:
    pool = await _get_pool()
    offset = (page - 1) * per_page

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            filters = ["1=1"]
            params: list = []

            if job_status:
                filters.append("status = %s")
                params.append(job_status)

            where = " AND ".join(filters)
            await cur.execute(
                f"""SELECT j.id, j.library_id, j.file_index, j.status, j.strategy,
                          j.progress_pct, j.error_message, j.created_at, j.started_at, j.finished_at,
                          COUNT(*) OVER() AS total_count
                   FROM hls_jobs j
                   WHERE {where}
                   ORDER BY j.created_at DESC
                   LIMIT %s OFFSET %s""",
                params + [per_page, offset],
            )
            rows = await cur.fetchall()

    total = rows[0][10] if rows else 0
    cols = ["id", "library_id", "file_index", "status", "strategy",
            "progress_pct", "error_message", "created_at", "started_at", "finished_at"]
    return {
        "items": [dict(zip(cols, r[:10])) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
