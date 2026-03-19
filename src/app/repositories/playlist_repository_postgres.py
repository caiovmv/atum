"""Repositório de playlists, favoritos e contagem de reproduções. PostgreSQL."""

from __future__ import annotations

from ..db_postgres import connection_postgres


def _database_url() -> str:
    from ..config import get_settings
    url = (get_settings().database_url or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL é obrigatório para playlists.")
    return url


# ---------------------------------------------------------------------------
# Playlists CRUD
# ---------------------------------------------------------------------------

def list_playlists(kind: str | None = None) -> list[dict]:
    """Lista todas as playlists com contagem de tracks. Filtra por kind se fornecido."""
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            sql = """
                SELECT p.id, p.name, p.cover_path, p.system_kind, p.kind,
                       p.description, p.ai_prompt, p.ai_notes, p.rules,
                       p.created_at, p.updated_at,
                       COALESCE(c.cnt, 0) AS track_count
                FROM playlists p
                LEFT JOIN (
                    SELECT playlist_id, COUNT(*) AS cnt FROM playlist_tracks GROUP BY playlist_id
                ) c ON c.playlist_id = p.id
            """
            params: list = []
            if kind:
                sql += " WHERE p.kind = %s"
                params.append(kind)
            sql += """
                ORDER BY
                    CASE WHEN p.system_kind IS NOT NULL THEN 0 ELSE 1 END,
                    p.created_at DESC
            """
            cur.execute(sql, params)
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                if d.get("rules") and isinstance(d["rules"], str):
                    import json
                    d["rules"] = json.loads(d["rules"])
                rows.append(d)
            return rows


def get_playlist(playlist_id: int) -> dict | None:
    """Retorna playlist com tracks enriquecidas (join com downloads/library_imports)."""
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, cover_path, system_kind, kind, rules, ai_prompt, ai_notes, description, created_at, updated_at FROM playlists WHERE id = %s",
                (playlist_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            playlist = dict(row)
            if playlist.get("rules") and isinstance(playlist["rules"], str):
                import json as _json
                playlist["rules"] = _json.loads(playlist["rules"])

            if playlist.get("system_kind") == "most_played":
                cur.execute("""
                    SELECT
                        t.id, t.source, t.item_id, t.file_index, t.file_name,
                        pc.play_count,
                        COALESCE(d.name, li.name) AS item_name,
                        COALESCE(li.artist, '') AS artist,
                        COALESCE(d.cover_path_small, li.cover_path_small) AS cover_path_small
                    FROM track_play_counts pc
                    LEFT JOIN playlist_tracks t
                        ON t.source = pc.source AND t.item_id = pc.item_id AND t.file_index = pc.file_index
                        AND t.playlist_id = %s
                    LEFT JOIN downloads d ON pc.source = 'download' AND d.id = pc.item_id
                    LEFT JOIN library_imports li ON pc.source = 'import' AND li.id = pc.item_id
                    WHERE pc.play_count > 0
                    ORDER BY pc.play_count DESC, pc.last_played_at DESC
                    LIMIT 500
                """, (playlist_id,))
                tracks = []
                for tr in cur.fetchall():
                    t = dict(tr)
                    t.setdefault("position", 0)
                    tracks.append(t)
                playlist["tracks"] = tracks
            else:
                cur.execute("""
                    SELECT
                        pt.id, pt.source, pt.item_id, pt.file_index, pt.file_name, pt.position, pt.added_at,
                        COALESCE(d.name, li.name) AS item_name,
                        COALESCE(li.artist, '') AS artist,
                        COALESCE(d.cover_path_small, li.cover_path_small) AS cover_path_small
                    FROM playlist_tracks pt
                    LEFT JOIN downloads d ON pt.source = 'download' AND d.id = pt.item_id
                    LEFT JOIN library_imports li ON pt.source = 'import' AND li.id = pt.item_id
                    WHERE pt.playlist_id = %s
                    ORDER BY pt.position, pt.added_at
                """, (playlist_id,))
                playlist["tracks"] = [dict(r) for r in cur.fetchall()]

            return playlist


def create_playlist(
    name: str,
    kind: str = "static",
    rules: list[dict] | None = None,
    ai_prompt: str | None = None,
    description: str | None = None,
) -> int:
    import json as _json
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO playlists (name, kind, rules, ai_prompt, description)
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (
                    name.strip(),
                    kind,
                    _json.dumps(rules) if rules else None,
                    ai_prompt,
                    description,
                ),
            )
            pid = cur.fetchone()["id"]
            conn.commit()
            return pid


def update_playlist(
    playlist_id: int,
    name: str | None = None,
    cover_path: str | None = None,
    rules: list[dict] | None = None,
    ai_prompt: str | None = None,
    ai_notes: str | None = None,
    description: str | None = None,
) -> bool:
    import json as _json
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT system_kind FROM playlists WHERE id = %s", (playlist_id,))
            row = cur.fetchone()
            if not row:
                return False
            updates = []
            params: list = []
            if name is not None:
                updates.append("name = %s")
                params.append(name.strip())
            if cover_path is not None:
                updates.append("cover_path = %s")
                params.append(cover_path)
            if rules is not None:
                updates.append("rules = %s")
                params.append(_json.dumps(rules))
            if ai_prompt is not None:
                updates.append("ai_prompt = %s")
                params.append(ai_prompt)
            if ai_notes is not None:
                updates.append("ai_notes = %s")
                params.append(ai_notes)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
            if not updates:
                return True
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(playlist_id)
            cur.execute(
                f"UPDATE playlists SET {', '.join(updates)} WHERE id = %s",
                params,
            )
            conn.commit()
            return True


def delete_playlist(playlist_id: int) -> bool:
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT system_kind FROM playlists WHERE id = %s", (playlist_id,))
            row = cur.fetchone()
            if not row:
                return False
            if row["system_kind"] is not None:
                raise ValueError("Playlists do sistema não podem ser removidas.")
            cur.execute("DELETE FROM playlists WHERE id = %s", (playlist_id,))
            conn.commit()
            return True


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------

def add_tracks(playlist_id: int, tracks: list[dict]) -> int:
    """Adiciona tracks à playlist. Retorna quantidade inserida."""
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(position) AS mx FROM playlist_tracks WHERE playlist_id = %s", (playlist_id,))
            mx = cur.fetchone()["mx"] or 0
            inserted = 0
            for t in tracks:
                mx += 1
                try:
                    cur.execute(
                        """INSERT INTO playlist_tracks (playlist_id, source, item_id, file_index, file_name, position)
                           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                        (playlist_id, t["source"], t["item_id"], t.get("file_index", 0), t.get("file_name"), mx),
                    )
                    inserted += cur.rowcount
                except Exception:
                    pass
            conn.commit()
            return inserted


def replace_tracks(playlist_id: int, tracks: list[dict]) -> int:
    """Remove todas as tracks e insere as novas. Retorna quantidade inserida."""
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM playlist_tracks WHERE playlist_id = %s", (playlist_id,))
            inserted = 0
            for i, t in enumerate(tracks):
                try:
                    cur.execute(
                        """INSERT INTO playlist_tracks (playlist_id, source, item_id, file_index, file_name, position)
                           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                        (playlist_id, t["source"], t["item_id"], t.get("file_index", 0), t.get("file_name"), i),
                    )
                    inserted += cur.rowcount
                except Exception:
                    pass
            conn.commit()
            return inserted


def remove_track(playlist_id: int, track_id: int) -> bool:
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM playlist_tracks WHERE id = %s AND playlist_id = %s",
                (track_id, playlist_id),
            )
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted


def reorder_tracks(playlist_id: int, track_ids: list[int]) -> None:
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            for pos, tid in enumerate(track_ids):
                cur.execute(
                    "UPDATE playlist_tracks SET position = %s WHERE id = %s AND playlist_id = %s",
                    (pos, tid, playlist_id),
                )
            conn.commit()


# ---------------------------------------------------------------------------
# Favoritos
# ---------------------------------------------------------------------------

def _favorites_id() -> int:
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM playlists WHERE system_kind = 'favorites'")
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Playlist de favoritos não encontrada.")
            return row["id"]


def toggle_favorite(source: str, item_id: int, file_index: int = 0, file_name: str | None = None) -> bool:
    """Retorna True se adicionou, False se removeu."""
    fav_id = _favorites_id()
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM playlist_tracks WHERE playlist_id = %s AND source = %s AND item_id = %s AND file_index = %s",
                (fav_id, source, item_id, file_index),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute("DELETE FROM playlist_tracks WHERE id = %s", (existing["id"],))
                conn.commit()
                return False
            else:
                cur.execute("SELECT COALESCE(MAX(position), 0) + 1 AS pos FROM playlist_tracks WHERE playlist_id = %s", (fav_id,))
                pos = cur.fetchone()["pos"]
                cur.execute(
                    """INSERT INTO playlist_tracks (playlist_id, source, item_id, file_index, file_name, position)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (fav_id, source, item_id, file_index, file_name, pos),
                )
                conn.commit()
                return True


def check_favorites_batch(tracks: list[dict]) -> list[dict]:
    """Recebe lista de {source, item_id, file_index} e retorna apenas os favoritados."""
    if not tracks:
        return []
    fav_id = _favorites_id()
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            conditions = []
            params: list = [fav_id]
            for t in tracks:
                conditions.append("(source = %s AND item_id = %s AND file_index = %s)")
                params.extend([t["source"], t["item_id"], t.get("file_index", 0)])
            where = " OR ".join(conditions)
            cur.execute(
                f"SELECT source, item_id, file_index FROM playlist_tracks WHERE playlist_id = %s AND ({where})",
                params,
            )
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Play counts
# ---------------------------------------------------------------------------

def increment_play_count(source: str, item_id: int, file_index: int = 0) -> int:
    """Incrementa e retorna novo play_count."""
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO track_play_counts (source, item_id, file_index, play_count, last_played_at)
                VALUES (%s, %s, %s, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (source, item_id, file_index)
                DO UPDATE SET play_count = track_play_counts.play_count + 1, last_played_at = CURRENT_TIMESTAMP
                RETURNING play_count
            """, (source, item_id, file_index))
            count = cur.fetchone()["play_count"]
            conn.commit()
            return count


def reset_play_counts() -> int:
    """Zera todos os contadores. Retorna quantidade removida."""
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM track_play_counts")
            deleted = cur.rowcount
            conn.commit()
            return deleted


def get_most_played(limit: int = 100) -> list[dict]:
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pc.source, pc.item_id, pc.file_index, pc.play_count, pc.last_played_at,
                       COALESCE(d.name, li.name) AS item_name,
                       COALESCE(li.artist, '') AS artist
                FROM track_play_counts pc
                LEFT JOIN downloads d ON pc.source = 'download' AND d.id = pc.item_id
                LEFT JOIN library_imports li ON pc.source = 'import' AND li.id = pc.item_id
                WHERE pc.play_count > 0
                ORDER BY pc.play_count DESC, pc.last_played_at DESC
                LIMIT %s
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def get_playlist_tracks_with_paths(playlist_id: int) -> list[dict]:
    """Retorna tracks da playlist com content_path resolvido para download."""
    with connection_postgres(_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    pt.id, pt.source, pt.item_id, pt.file_index, pt.file_name, pt.position,
                    COALESCE(d.content_path, li.content_path) AS content_path,
                    COALESCE(d.name, li.name) AS item_name,
                    d.torrent_files
                FROM playlist_tracks pt
                LEFT JOIN downloads d ON pt.source = 'download' AND d.id = pt.item_id
                LEFT JOIN library_imports li ON pt.source = 'import' AND li.id = pt.item_id
                WHERE pt.playlist_id = %s
                ORDER BY pt.position, pt.added_at
            """, (playlist_id,))
            return [dict(r) for r in cur.fetchall()]
