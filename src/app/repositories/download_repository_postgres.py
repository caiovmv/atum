"""Implementação de DownloadRepository para PostgreSQL (usado quando DATABASE_URL está definido)."""

from __future__ import annotations

from ..db_postgres import connection_postgres
from ..domain import DownloadStatus
from ..domain.ports import DownloadRepository

DOWNLOAD_COLUMNS = (
    "id, magnet, name, save_path, status, progress, pid, error_message, added_at, updated_at"
    ", num_seeds, num_peers, download_speed_bps, total_bytes, downloaded_bytes, eta_seconds"
    ", content_path, content_type"
    ", cover_path_small, cover_path_large"
    ", year, video_quality_label, audio_codec, music_quality"
    ", excluded_file_indices, torrent_files"
    ", tmdb_id, imdb_id, library_path, post_processed, previous_content_path"
)


def _apply_defaults(rows: list[dict]) -> None:
    import json
    for row in rows:
        for k in ("num_seeds", "num_peers", "download_speed_bps", "total_bytes", "downloaded_bytes", "eta_seconds",
                  "content_path", "content_type", "cover_path_small", "cover_path_large",
                  "year", "video_quality_label", "audio_codec", "music_quality", "excluded_file_indices", "torrent_files"):
            row.setdefault(k, None)
        raw = row.get("excluded_file_indices")
        if isinstance(raw, str) and raw.strip():
            try:
                row["excluded_file_indices"] = json.loads(raw)
            except (ValueError, TypeError):
                row["excluded_file_indices"] = []
        elif raw is None or (isinstance(raw, list) and not raw):
            row["excluded_file_indices"] = []
        elif not isinstance(row.get("excluded_file_indices"), list):
            row["excluded_file_indices"] = []
        tf = row.get("torrent_files")
        if tf is not None and not isinstance(tf, list):
            row["torrent_files"] = None


class PostgresDownloadRepository:
    """Implementação de DownloadRepository para PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def add(
        self,
        magnet: str,
        save_path: str,
        name: str | None = None,
        content_type: str | None = None,
        excluded_file_indices: list[int] | None = None,
    ) -> int:
        import json
        indices_json = json.dumps(excluded_file_indices) if excluded_file_indices else None
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO downloads (magnet, name, save_path, status, content_type, excluded_file_indices) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (magnet.strip(), (name or "").strip() or None, save_path, DownloadStatus.QUEUED.value,
                     content_type if content_type in ("music", "movies", "tv") else None, indices_json),
                )
                row = cur.fetchone()
                conn.commit()
                return row["id"] or 0

    def list(self, status_filter: str | None = None) -> list[dict]:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                if status_filter:
                    cur.execute(
                        f"SELECT {DOWNLOAD_COLUMNS} FROM downloads WHERE status = %s ORDER BY id DESC",
                        (status_filter,),
                    )
                else:
                    cur.execute(f"SELECT {DOWNLOAD_COLUMNS} FROM downloads ORDER BY id DESC")
                rows = [dict(r) for r in cur.fetchall()]
        _apply_defaults(rows)
        return rows

    def get(self, download_id: int) -> dict | None:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {DOWNLOAD_COLUMNS} FROM downloads WHERE id = %s",
                    (download_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        out = dict(row)
        _apply_defaults([out])
        return out

    def update_status(
        self,
        download_id: int,
        status: str,
        error_message: str | None = None,
        progress: float | None = None,
    ) -> None:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                if progress is not None:
                    cur.execute(
                        "UPDATE downloads SET status = %s, error_message = %s, progress = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (status, error_message, progress, download_id),
                    )
                else:
                    cur.execute(
                        "UPDATE downloads SET status = %s, error_message = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                        (status, error_message, download_id),
                    )
            conn.commit()

    def set_pid(self, download_id: int, pid: int | None) -> None:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE downloads SET pid = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (pid, download_id),
                )
            conn.commit()

    def set_content_path(self, download_id: int, content_path: str | None) -> None:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE downloads SET content_path = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (content_path, download_id),
                )
            conn.commit()

    def set_cover_paths(
        self,
        download_id: int,
        cover_path_small: str | None = None,
        cover_path_large: str | None = None,
    ) -> None:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE downloads SET cover_path_small = %s, cover_path_large = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (cover_path_small, cover_path_large, download_id),
                )
            conn.commit()

    def set_torrent_files(self, download_id: int, files: list[dict] | None) -> None:
        import json
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE downloads SET torrent_files = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (json.dumps(files) if files else None, download_id),
                )
            conn.commit()

    def update_progress(
        self,
        download_id: int,
        *,
        progress: float | None = None,
        num_seeds: int | None = None,
        num_peers: int | None = None,
        download_speed_bps: int | None = None,
        total_bytes: int | None = None,
        downloaded_bytes: int | None = None,
        eta_seconds: float | None = None,
    ) -> None:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                updates = ["updated_at = CURRENT_TIMESTAMP"]
                args = []
                if progress is not None:
                    updates.append("progress = %s")
                    args.append(progress)
                if num_seeds is not None:
                    updates.append("num_seeds = %s")
                    args.append(num_seeds)
                if num_peers is not None:
                    updates.append("num_peers = %s")
                    args.append(num_peers)
                if download_speed_bps is not None:
                    updates.append("download_speed_bps = %s")
                    args.append(download_speed_bps)
                if total_bytes is not None:
                    updates.append("total_bytes = %s")
                    args.append(total_bytes)
                if downloaded_bytes is not None:
                    updates.append("downloaded_bytes = %s")
                    args.append(downloaded_bytes)
                if eta_seconds is not None:
                    updates.append("eta_seconds = %s")
                    args.append(eta_seconds)
                if args:
                    args.append(download_id)
                    cur.execute(
                        f"UPDATE downloads SET {', '.join(updates)} WHERE id = %s",
                        args,
                    )
            conn.commit()

    def update_enrichment(
        self,
        download_id: int,
        *,
        tmdb_id: int | None = None,
        imdb_id: str | None = None,
        library_path: str | None = None,
        post_processed: bool | None = None,
        content_type: str | None = None,
        previous_content_path: str | None = None,
    ) -> None:
        """Atualiza colunas de enriquecimento (TMDB/IMDB, library_path, post_processed)."""
        updates = ["updated_at = CURRENT_TIMESTAMP"]
        args: list = []
        if tmdb_id is not None:
            updates.append("tmdb_id = %s")
            args.append(tmdb_id)
        if imdb_id is not None:
            updates.append("imdb_id = %s")
            args.append(imdb_id)
        if library_path is not None:
            updates.append("library_path = %s")
            args.append(library_path)
        if post_processed is not None:
            updates.append("post_processed = %s")
            args.append(post_processed)
        if content_type is not None:
            updates.append("content_type = %s")
            args.append(content_type)
        if previous_content_path is not None:
            updates.append("previous_content_path = %s")
            args.append(previous_content_path)
        if len(args) == 0:
            return
        args.append(download_id)
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE downloads SET {', '.join(updates)} WHERE id = %s",
                    args,
                )
            conn.commit()

    def delete(self, download_id: int) -> bool:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM downloads WHERE id = %s", (download_id,))
                n = cur.rowcount
            conn.commit()
        return n > 0
