"""Repositório de library_imports para PostgreSQL."""

from __future__ import annotations

from ..db_postgres import connection_postgres


def _row_to_dict(row: dict) -> dict:
    import json
    out = dict(row)
    if "metadata_json" in out and isinstance(out.get("metadata_json"), str):
        try:
            out["metadata_json"] = json.loads(out["metadata_json"]) if out["metadata_json"] else None
        except (ValueError, TypeError):
            out["metadata_json"] = None
    if "tags" in out and out.get("tags") is not None and not isinstance(out["tags"], list):
        try:
            out["tags"] = json.loads(out["tags"]) if isinstance(out["tags"], str) else (out["tags"] or [])
        except (ValueError, TypeError):
            out["tags"] = []
    if "tags" in out and out["tags"] is None:
        out["tags"] = []
    return out


class LibraryImportRepositoryPostgres:
    """CRUD para library_imports (itens descobertos pelo sync nas pastas de biblioteca)."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def add(
        self,
        content_path: str,
        content_type: str,
        name: str,
        year: int | None = None,
        metadata_json: dict | None = None,
        cover_path_small: str | None = None,
        cover_path_large: str | None = None,
        artist: str | None = None,
        album: str | None = None,
        genre: str | None = None,
        tags: list[str] | None = None,
    ) -> int:
        import json
        meta = json.dumps(metadata_json) if metadata_json else None
        tags_json = json.dumps(tags if tags is not None else [])
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO library_imports
                       (content_path, content_type, name, year, metadata_json, cover_path_small, cover_path_large,
                        artist, album, genre, tags)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                       ON CONFLICT (content_path) DO UPDATE SET
                         name = EXCLUDED.name,
                         year = EXCLUDED.year,
                         metadata_json = EXCLUDED.metadata_json,
                         cover_path_small = EXCLUDED.cover_path_small,
                         cover_path_large = EXCLUDED.cover_path_large,
                         artist = EXCLUDED.artist,
                         album = EXCLUDED.album,
                         genre = EXCLUDED.genre,
                         tags = EXCLUDED.tags,
                         updated_at = CURRENT_TIMESTAMP
                       RETURNING id""",
                    (
                        content_path,
                        content_type if content_type in ("music", "movies", "tv") else "music",
                        name,
                        year,
                        meta,
                        cover_path_small,
                        cover_path_large,
                        (artist or "").strip() or None,
                        (album or "").strip() or None,
                        (genre or "").strip() or None,
                        tags_json,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return row["id"] or 0

    def list(
        self,
        content_type: str | None = None,
        artist: str | None = None,
        album: str | None = None,
        genre: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        sel = """SELECT id, content_path, content_type, name, year, metadata_json,
                         cover_path_small, cover_path_large, artist, album, genre, tags,
                         created_at, updated_at
                  FROM library_imports"""
        conditions = []
        params = []
        if content_type and (content_type or "").strip().lower() in ("music", "movies", "tv"):
            conditions.append("content_type = %s")
            params.append(content_type.strip().lower())
        if artist and (artist or "").strip():
            conditions.append("TRIM(COALESCE(artist, '')) = %s")
            params.append(artist.strip())
        if album and (album or "").strip():
            conditions.append("TRIM(COALESCE(album, '')) = %s")
            params.append(album.strip())
        if genre and (genre or "").strip():
            conditions.append("TRIM(COALESCE(genre, '')) = %s")
            params.append(genre.strip())
        if tags:
            # item must have at least one of the requested tags (containment: tags @> '["x"]')
            tags_clean = [t.strip() for t in tags if (t or "").strip()]
            if tags_clean:
                import json
                or_parts = ["tags @> %s::jsonb"] * len(tags_clean)
                conditions.append("(" + " OR ".join(or_parts) + ")")
                params.extend(json.dumps([t]) for t in tags_clean)
        if conditions:
            sel += " WHERE " + " AND ".join(conditions)
        sel += " ORDER BY content_type, name"
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sel, params or None)
                rows = [_row_to_dict(dict(r)) for r in cur.fetchall()]
        return rows

    def get_update_marker(self) -> tuple[int, str | None]:
        """Retorna (count, max_updated_at_iso) para detectar alterações na biblioteca."""
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS c, MAX(updated_at) AS m FROM library_imports"
                )
                row = cur.fetchone()
        count = int(row["c"]) if row and row.get("c") is not None else 0
        max_at = row.get("m")
        if max_at is not None and hasattr(max_at, "isoformat"):
            max_at = max_at.isoformat()
        elif max_at is not None:
            max_at = str(max_at)
        return (count, max_at)

    def get(self, import_id: int) -> dict | None:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, content_path, content_type, name, year, metadata_json,
                              cover_path_small, cover_path_large, artist, album, genre, tags,
                              created_at, updated_at
                       FROM library_imports WHERE id = %s""",
                    (import_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return _row_to_dict(dict(row))

    def get_by_content_path(self, content_path: str) -> dict | None:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, content_path, content_type, name, year, metadata_json,
                              cover_path_small, cover_path_large, artist, album, genre, tags,
                              created_at, updated_at
                       FROM library_imports WHERE content_path = %s""",
                    (content_path,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return _row_to_dict(dict(row))

    def update_metadata(
        self,
        import_id: int,
        name: str | None = None,
        year: int | None = None,
        metadata_json: dict | None = None,
        cover_path_small: str | None = None,
        cover_path_large: str | None = None,
        artist: str | None = None,
        album: str | None = None,
        genre: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        import json
        updates = []
        params = []
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if year is not None:
            updates.append("year = %s")
            params.append(year)
        if metadata_json is not None:
            updates.append("metadata_json = %s")
            params.append(json.dumps(metadata_json))
        if cover_path_small is not None:
            updates.append("cover_path_small = %s")
            params.append(cover_path_small)
        if cover_path_large is not None:
            updates.append("cover_path_large = %s")
            params.append(cover_path_large)
        if artist is not None:
            updates.append("artist = %s")
            params.append((artist or "").strip() or None)
        if album is not None:
            updates.append("album = %s")
            params.append((album or "").strip() or None)
        if genre is not None:
            updates.append("genre = %s")
            params.append((genre or "").strip() or None)
        if tags is not None:
            updates.append("tags = %s::jsonb")
            params.append(json.dumps(tags))
        if not updates:
            return True
        params.append(import_id)
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE library_imports SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    params,
                )
                conn.commit()
                return cur.rowcount > 0

    def get_facets(self, content_type: str | None = None) -> dict:
        """Retorna listas de valores distintos para artist, album, genre (e tags) para filtrar/agrupar.
        Para music: artists, albums, genres. Para movies/tv: genres. Inclui tags em todos."""
        import json
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                where = ""
                params = []
                if content_type and (content_type or "").strip().lower() in ("music", "movies", "tv"):
                    where = " WHERE content_type = %s"
                    params.append(content_type.strip().lower())
                artists, albums, genres, all_tags = [], [], [], []
                cur.execute(
                    """SELECT DISTINCT TRIM(artist) AS v FROM library_imports
                       """ + where + """ AND TRIM(COALESCE(artist, '')) != '' ORDER BY 1""",
                    params or None,
                )
                artists = [r["v"] for r in cur.fetchall()]
                cur.execute(
                    """SELECT DISTINCT TRIM(album) AS v FROM library_imports
                       """ + where + """ AND TRIM(COALESCE(album, '')) != '' ORDER BY 1""",
                    params or None,
                )
                albums = [r["v"] for r in cur.fetchall()]
                cur.execute(
                    """SELECT DISTINCT TRIM(genre) AS v FROM library_imports
                       """ + where + """ AND TRIM(COALESCE(genre, '')) != '' ORDER BY 1""",
                    params or None,
                )
                genres = [r["v"] for r in cur.fetchall()]
                cur.execute(
                    """SELECT tags FROM library_imports""" + where,
                    params or None,
                )
                seen = set()
                for r in cur.fetchall():
                    t = r.get("tags")
                    if isinstance(t, list):
                        for x in t:
                            if isinstance(x, str) and x.strip() and x.strip() not in seen:
                                seen.add(x.strip())
                                all_tags.append(x.strip())
                    elif isinstance(t, str):
                        try:
                            arr = json.loads(t) if t else []
                            for x in arr:
                                if isinstance(x, str) and x.strip() and x.strip() not in seen:
                                    seen.add(x.strip())
                                    all_tags.append(x.strip())
                        except (ValueError, TypeError):
                            pass
                all_tags.sort()
        return {"artists": artists, "albums": albums, "genres": genres, "tags": all_tags}

    def delete(self, import_id: int) -> bool:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM library_imports WHERE id = %s", (import_id,))
                conn.commit()
                return cur.rowcount > 0

    def delete_by_content_path(self, content_path: str) -> bool:
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM library_imports WHERE content_path = %s", (content_path,))
                conn.commit()
                return cur.rowcount > 0
