"""Implementação de DownloadRepository para PostgreSQL (usado quando DATABASE_URL está definido)."""

from __future__ import annotations

from ..db_postgres import connection_postgres
from ..domain import DownloadStatus
from ..domain.ports import DownloadRepository

_DEFAULT_LIMIT = 5000

DOWNLOAD_COLUMNS = (
    "id, magnet, torrent_url, name, save_path, status, progress, pid, error_message, added_at, updated_at"
    ", num_seeds, num_peers, download_speed_bps, total_bytes, downloaded_bytes, eta_seconds"
    ", content_path, content_type"
    ", cover_path_small, cover_path_large"
    ", year, video_quality_label, audio_codec, music_quality"
    ", excluded_file_indices, torrent_files"
    ", tmdb_id, imdb_id, library_path, post_processed, previous_content_path"
    ", artist, album, genre, tags"
    ", bpm, musical_key, energy, danceability, valence, loudness_db, replaygain_db"
    ", musicbrainz_id, sub_genres, moods, descriptors, record_label, release_type"
    ", overview, vote_average, runtime_minutes, backdrop_path, original_title, tmdb_genres"
    ", enriched_at, enrichment_sources"
)


def _apply_defaults(rows: list[dict]) -> None:
    import json
    for row in rows:
        for k in ("torrent_url", "num_seeds", "num_peers", "download_speed_bps", "total_bytes", "downloaded_bytes", "eta_seconds",
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
        if "tags" in row and row.get("tags") is not None and not isinstance(row["tags"], list):
            try:
                row["tags"] = json.loads(row["tags"]) if isinstance(row["tags"], str) else (row["tags"] or [])
            except (ValueError, TypeError):
                row["tags"] = []
        if "tags" in row and row["tags"] is None:
            row["tags"] = []


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
        torrent_url: str | None = None,
    ) -> int:
        import json
        indices_json = json.dumps(excluded_file_indices) if excluded_file_indices else None
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO downloads (magnet, torrent_url, name, save_path, status, content_type, excluded_file_indices)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (magnet.strip(), (torrent_url or "").strip() or None,
                     (name or "").strip() or None, save_path, DownloadStatus.QUEUED.value,
                     content_type if content_type in ("music", "movies", "tv") else None, indices_json),
                )
                row = cur.fetchone()
                conn.commit()
                return row["id"] or 0

    def list(
        self,
        status_filter: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        q: str | None = None,
        content_type: str | None = None,
    ) -> list[dict]:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                conditions: list[str] = []
                params: list = []
                if status_filter:
                    conditions.append("status = %s")
                    params.append(status_filter)
                if content_type and content_type.strip().lower() in ("music", "movies", "tv"):
                    conditions.append("content_type = %s")
                    params.append(content_type.strip().lower())
                if q and q.strip():
                    terms = q.strip().split()
                    tsquery = " & ".join(t + ":*" for t in terms if t)
                    conditions.append("search_vector @@ to_tsquery('simple', %s)")
                    params.append(tsquery)
                sql = f"SELECT {DOWNLOAD_COLUMNS} FROM downloads"
                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)
                if q and q.strip():
                    terms = q.strip().split()
                    tsquery_rank = " & ".join(t + ":*" for t in terms if t)
                    sql += f" ORDER BY ts_rank(search_vector, to_tsquery('simple', %s)) DESC, id DESC"
                    params.append(tsquery_rank)
                else:
                    sql += " ORDER BY id DESC"
                effective_limit = limit if limit is not None and limit > 0 else _DEFAULT_LIMIT
                sql += " LIMIT %s"
                params.append(effective_limit)
                if offset is not None and offset > 0:
                    sql += " OFFSET %s"
                    params.append(offset)
                cur.execute(sql, params or None)
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
        artist: str | None = None,
        album: str | None = None,
        genre: str | None = None,
    ) -> None:
        """Atualiza colunas de enriquecimento (TMDB/IMDB, library_path, post_processed, artist/album/genre)."""
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
        if artist is not None:
            updates.append("artist = %s")
            args.append((artist or "").strip() or None)
        if album is not None:
            updates.append("album = %s")
            args.append((album or "").strip() or None)
        if genre is not None:
            updates.append("genre = %s")
            args.append((genre or "").strip() or None)
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

    def update_tags(self, download_id: int, tags: list[str]) -> None:
        import json
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE downloads SET tags = %s::jsonb, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (json.dumps(tags), download_id),
                )
            conn.commit()

    def update_full_enrichment(
        self,
        download_id: int,
        **kwargs,
    ) -> None:
        """Atualiza todas as colunas de enrichment de um download (BPM, moods, etc.)."""
        _ALLOWED = {
            "bpm", "musical_key", "energy", "danceability", "valence",
            "loudness_db", "replaygain_db", "musicbrainz_id", "sub_genres",
            "moods", "descriptors", "record_label", "release_type",
            "overview", "vote_average", "runtime_minutes", "backdrop_path",
            "original_title", "tmdb_genres", "enriched_at", "enrichment_sources",
            "enrichment_error", "artist", "album", "genre",
            "tmdb_id", "imdb_id", "content_type",
        }
        updates = ["updated_at = CURRENT_TIMESTAMP"]
        args: list = []
        for k, v in kwargs.items():
            if k in _ALLOWED and v is not None:
                updates.append(f"{k} = %s")
                args.append(v)
        if not args:
            return
        args.append(download_id)
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE downloads SET {', '.join(updates)} WHERE id = %s",
                    args,
                )
            conn.commit()

    def list_pending_enrichment(self, limit: int = 10) -> list[dict]:
        """Retorna downloads completed sem enrichment para o daemon processar."""
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""SELECT {DOWNLOAD_COLUMNS} FROM downloads
                        WHERE status = 'completed'
                          AND content_path IS NOT NULL
                          AND (enriched_at IS NULL AND enrichment_error IS NULL)
                        ORDER BY added_at ASC
                        LIMIT %s""",
                    (limit,),
                )
                rows = [dict(r) for r in cur.fetchall()]
        _apply_defaults(rows)
        return rows

    def delete(self, download_id: int) -> bool:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM downloads WHERE id = %s", (download_id,))
                n = cur.rowcount
            conn.commit()
        return n > 0
