"""Admin: visão geral de storage — MinIO, HLS jobs, fila de sync."""

from fastapi import APIRouter, Query

from ...auth_service import AuthUser, require_backoffice

router = APIRouter(prefix="/storage")


async def _get_pool():
    from ....db_postgres import get_async_pool
    from ....config import get_settings
    return await get_async_pool(get_settings().database_url)


@router.get("/overview")
async def storage_overview(
    actor: AuthUser = require_backoffice("super_admin", "financial"),
) -> dict:
    """Resumo de uso de storage: MinIO buckets, HLS jobs ativos, fila de sync."""
    from ....storage_service import ALL_BUCKETS, BUCKET_HLS, BUCKET_MUSIC, BUCKET_COVERS, get_storage

    storage = get_storage()
    bucket_usage: dict = {}
    total_bytes = 0
    for bucket in ALL_BUCKETS:
        try:
            size = storage.bucket_size_bytes(bucket)
            bucket_usage[bucket] = {"bytes": size, "gb": round(size / 1024**3, 3)}
            total_bytes += size
        except Exception as e:
            bucket_usage[bucket] = {"bytes": 0, "gb": 0, "error": str(e)}

    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # HLS jobs por status
            await cur.execute(
                "SELECT status, COUNT(*) FROM hls_jobs GROUP BY status"
            )
            hls_by_status = {r[0]: r[1] for r in await cur.fetchall()}

            # Top 10 famílias por uso de storage
            await cur.execute(
                """SELECT sa.family_id, f.name,
                          COALESCE(SUM(sa.quantity) FILTER (WHERE sa.addon_type = 'storage_gb'), 0) AS addon_gb,
                          p.base_storage_gb
                   FROM families f
                   JOIN plans p ON p.id = f.plan_id
                   LEFT JOIN storage_addons sa ON sa.family_id = f.id AND sa.active
                   GROUP BY f.id, f.name, p.base_storage_gb
                   ORDER BY (p.base_storage_gb + COALESCE(SUM(sa.quantity) FILTER (WHERE sa.addon_type = 'storage_gb'), 0)) DESC
                   LIMIT 10"""
            )
            top_families = [
                {"family_id": str(r[0]), "name": r[1],
                 "addon_gb": r[2], "base_gb": r[3], "total_gb": r[3] + r[2]}
                for r in await cur.fetchall()
            ]

            # Fila de cloud sync
            await cur.execute(
                "SELECT status, COUNT(*) FROM cloud_sync_queue GROUP BY status"
            )
            sync_queue = {r[0]: r[1] for r in await cur.fetchall()}

    return {
        "minio": {
            "total_bytes": total_bytes,
            "total_gb": round(total_bytes / 1024**3, 3),
            "buckets": bucket_usage,
        },
        "hls_jobs": hls_by_status,
        "cloud_sync_queue": sync_queue,
        "top_families_by_quota": top_families,
    }


@router.get("/hls-jobs")
async def list_hls_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    job_status: str | None = Query(None, alias="status"),
    actor: AuthUser = require_backoffice("super_admin"),
) -> dict:
    """Lista jobs HLS com paginação."""
    pool = await _get_pool()
    offset = (page - 1) * per_page

    filters = ["1=1"]
    params: list = []
    if job_status:
        filters.append("status = %s")
        params.append(job_status)

    where = " AND ".join(filters)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""SELECT id, family_id, library_id, file_index, status,
                          strategy, progress_pct, minio_prefix, error_msg,
                          last_accessed_at, created_at, updated_at,
                          COUNT(*) OVER() AS total
                   FROM hls_jobs WHERE {where}
                   ORDER BY updated_at DESC
                   LIMIT %s OFFSET %s""",
                params + [per_page, offset],
            )
            rows = await cur.fetchall()

    total = rows[0][12] if rows else 0
    cols = ["id", "family_id", "library_id", "file_index", "status",
            "strategy", "progress_pct", "minio_prefix", "error_msg",
            "last_accessed_at", "created_at", "updated_at"]
    return {
        "items": [dict(zip(cols, r[:12])) for r in rows],
        "total": total, "page": page, "per_page": per_page,
    }
