"""Repositório de library_imports para PostgreSQL."""

from __future__ import annotations

from ..db_postgres import connection_postgres

_UNSET = object()  # sentinel para distinguir "não fornecido" de None explícito


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
        q: str | None = None,
        mood: str | None = None,
        sub_genre: str | None = None,
        bpm_min: float | None = None,
        bpm_max: float | None = None,
    ) -> list[dict]:
        sel = """SELECT id, content_path, content_type, name, year, metadata_json,
                         cover_path_small, cover_path_large, artist, album, genre, tags,
                         tmdb_id, imdb_id, quality_label, previous_content_path,
                         bpm, musical_key, energy, danceability, valence, loudness_db,
                         replaygain_db, musicbrainz_id, sub_genres, moods, descriptors,
                         record_label, release_type, overview, vote_average,
                         runtime_minutes, backdrop_path, original_title, tmdb_genres,
                         enriched_at, enrichment_sources,
                         created_at, updated_at
                  FROM library_imports"""
        conditions: list[str] = []
        params: list[object] = []
        if content_type and content_type.strip().lower() in ("music", "movies", "tv"):
            conditions.append("content_type = %s")
            params.append(content_type.strip().lower())
        if artist and artist.strip():
            conditions.append("TRIM(COALESCE(artist, '')) = %s")
            params.append(artist.strip())
        if album and album.strip():
            conditions.append("TRIM(COALESCE(album, '')) = %s")
            params.append(album.strip())
        if genre and genre.strip():
            conditions.append("TRIM(COALESCE(genre, '')) = %s")
            params.append(genre.strip())
        if tags:
            tags_clean = [t.strip() for t in tags if (t or "").strip()]
            if tags_clean:
                import json
                or_parts = ["tags @> %s::jsonb"] * len(tags_clean)
                conditions.append("(" + " OR ".join(or_parts) + ")")
                params.extend(json.dumps([t]) for t in tags_clean)
        if q and q.strip():
            like = f"%{q.strip()}%"
            conditions.append(
                "(name ILIKE %s OR COALESCE(artist,'') ILIKE %s OR COALESCE(album,'') ILIKE %s)"
            )
            params.extend([like, like, like])
        if mood and mood.strip():
            conditions.append("moods @> %s::text[]")
            params.append([mood.strip()])
        if sub_genre and sub_genre.strip():
            conditions.append("sub_genres @> %s::text[]")
            params.append([sub_genre.strip()])
        if bpm_min is not None:
            conditions.append("bpm >= %s")
            params.append(bpm_min)
        if bpm_max is not None:
            conditions.append("bpm <= %s")
            params.append(bpm_max)
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
                              tmdb_id, imdb_id, quality_label, previous_content_path,
                              bpm, musical_key, energy, danceability, valence, loudness_db,
                              replaygain_db, musicbrainz_id, sub_genres, moods, descriptors,
                              record_label, release_type, overview, vote_average,
                              runtime_minutes, backdrop_path, original_title, tmdb_genres,
                              enriched_at, enrichment_sources,
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
                              tmdb_id, imdb_id, quality_label, previous_content_path,
                              bpm, musical_key, energy, danceability, valence, loudness_db,
                              replaygain_db, musicbrainz_id, sub_genres, moods, descriptors,
                              record_label, release_type, overview, vote_average,
                              runtime_minutes, backdrop_path, original_title, tmdb_genres,
                              enriched_at, enrichment_sources,
                              created_at, updated_at
                       FROM library_imports WHERE content_path = %s""",
                    (content_path,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return _row_to_dict(dict(row))

    def list_pending_enrichment(self, limit: int = 10, retry_after_hours: int = 0) -> list[dict]:
        """Retorna itens pendentes de enriquecimento.

        Inclui itens nunca enriquecidos e, se retry_after_hours > 0, itens com erro
        cujo enriched_at seja mais antigo que o intervalo (permitindo retry automático).
        """
        with connection_postgres(self._database_url) as conn:
            with conn.cursor() as cur:
                _claim = "enrichment_in_progress"
                _stale_minutes = 15
                if retry_after_hours > 0:
                    cur.execute(
                        """UPDATE library_imports
                              SET enrichment_error = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE id IN (
                              SELECT id FROM library_imports
                              WHERE (enriched_at IS NULL AND enrichment_error IS NULL)
                                 OR (enrichment_error IS NOT NULL
                                     AND enrichment_error != %s
                                     AND COALESCE(enriched_at, '1970-01-01'::timestamptz)
                                         < NOW() - INTERVAL '1 hour' * %s)
                                 OR (enrichment_error = %s
                                     AND updated_at < NOW() - INTERVAL '1 minute' * %s)
                              ORDER BY created_at ASC
                              LIMIT %s
                              FOR UPDATE SKIP LOCKED
                            )
                           RETURNING id, content_path, content_type, name, year, metadata_json,
                                     cover_path_small, cover_path_large, artist, album, genre, tags,
                                     tmdb_id, imdb_id, quality_label, previous_content_path,
                                     enrichment_error,
                                     created_at, updated_at""",
                        (_claim, _claim, retry_after_hours, _claim, _stale_minutes, limit),
                    )
                else:
                    cur.execute(
                        """UPDATE library_imports
                              SET enrichment_error = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE id IN (
                              SELECT id FROM library_imports
                              WHERE (enriched_at IS NULL AND enrichment_error IS NULL)
                                 OR (enrichment_error = %s
                                     AND updated_at < NOW() - INTERVAL '1 minute' * %s)
                              ORDER BY created_at ASC
                              LIMIT %s
                              FOR UPDATE SKIP LOCKED
                            )
                           RETURNING id, content_path, content_type, name, year, metadata_json,
                                     cover_path_small, cover_path_large, artist, album, genre, tags,
                                     tmdb_id, imdb_id, quality_label, previous_content_path,
                                     enrichment_error,
                                     created_at, updated_at""",
                        (_claim, _claim, _stale_minutes, limit),
                    )
                conn.commit()
                rows = [_row_to_dict(dict(r)) for r in cur.fetchall()]
        return rows

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
        content_path: str | None = None,
        tmdb_id: int | None = None,
        imdb_id: str | None = None,
        quality_label: str | None = None,
        previous_content_path: str | None = None,
        # Enrichment fields
        bpm: float | None = None,
        musical_key: str | None = None,
        energy: float | None = None,
        danceability: float | None = None,
        valence: float | None = None,
        loudness_db: float | None = None,
        replaygain_db: float | None = None,
        musicbrainz_id: str | None = None,
        sub_genres: list[str] | None = None,
        moods: list[str] | None = None,
        descriptors: list[str] | None = None,
        record_label: str | None = None,
        release_type: str | None = None,
        overview: str | None = None,
        vote_average: float | None = None,
        runtime_minutes: int | None = None,
        backdrop_path: str | None = None,
        original_title: str | None = None,
        tmdb_genres: list[str] | None = None,
        enriched_at: str | None = _UNSET,
        enrichment_sources: list[str] | None = None,
        enrichment_error: str | None = _UNSET,
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
        if content_path is not None:
            updates.append("content_path = %s")
            params.append(content_path)
        if tmdb_id is not None:
            updates.append("tmdb_id = %s")
            params.append(tmdb_id)
        if imdb_id is not None:
            updates.append("imdb_id = %s")
            params.append(imdb_id)
        if quality_label is not None:
            updates.append("quality_label = %s")
            params.append(quality_label)
        if previous_content_path is not None:
            updates.append("previous_content_path = %s")
            params.append(previous_content_path)
        if bpm is not None:
            updates.append("bpm = %s")
            params.append(bpm)
        if musical_key is not None:
            updates.append("musical_key = %s")
            params.append(musical_key)
        if energy is not None:
            updates.append("energy = %s")
            params.append(energy)
        if danceability is not None:
            updates.append("danceability = %s")
            params.append(danceability)
        if valence is not None:
            updates.append("valence = %s")
            params.append(valence)
        if loudness_db is not None:
            updates.append("loudness_db = %s")
            params.append(loudness_db)
        if replaygain_db is not None:
            updates.append("replaygain_db = %s")
            params.append(replaygain_db)
        if musicbrainz_id is not None:
            updates.append("musicbrainz_id = %s")
            params.append(musicbrainz_id)
        if sub_genres is not None:
            updates.append("sub_genres = %s")
            params.append(sub_genres)
        if moods is not None:
            updates.append("moods = %s")
            params.append(moods)
        if descriptors is not None:
            updates.append("descriptors = %s")
            params.append(descriptors)
        if record_label is not None:
            updates.append("record_label = %s")
            params.append(record_label)
        if release_type is not None:
            updates.append("release_type = %s")
            params.append(release_type)
        if overview is not None:
            updates.append("overview = %s")
            params.append(overview)
        if vote_average is not None:
            updates.append("vote_average = %s")
            params.append(vote_average)
        if runtime_minutes is not None:
            updates.append("runtime_minutes = %s")
            params.append(runtime_minutes)
        if backdrop_path is not None:
            updates.append("backdrop_path = %s")
            params.append(backdrop_path)
        if original_title is not None:
            updates.append("original_title = %s")
            params.append(original_title)
        if tmdb_genres is not None:
            updates.append("tmdb_genres = %s")
            params.append(tmdb_genres)
        if enriched_at is not _UNSET:
            updates.append("enriched_at = %s")
            params.append(enriched_at)
        if enrichment_sources is not None:
            updates.append("enrichment_sources = %s")
            params.append(enrichment_sources)
        if enrichment_error is not _UNSET:
            updates.append("enrichment_error = %s")
            params.append(enrichment_error)
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
                where = " WHERE 1=1"
                params: list = []
                if content_type and content_type.strip().lower() in ("music", "movies", "tv"):
                    where += " AND content_type = %s"
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

                # Enrichment facets: moods and sub_genres (Postgres text[] columns)
                all_moods: list[str] = []
                all_sub_genres: list[str] = []
                cur.execute(
                    """SELECT DISTINCT unnest(moods) AS v FROM library_imports"""
                    + where + """ AND moods IS NOT NULL ORDER BY 1""",
                    params or None,
                )
                all_moods = [r["v"] for r in cur.fetchall() if r.get("v")]
                cur.execute(
                    """SELECT DISTINCT unnest(sub_genres) AS v FROM library_imports"""
                    + where + """ AND sub_genres IS NOT NULL ORDER BY 1""",
                    params or None,
                )
                all_sub_genres = [r["v"] for r in cur.fetchall() if r.get("v")]

        return {
            "artists": artists, "albums": albums, "genres": genres, "tags": all_tags,
            "moods": all_moods, "sub_genres": all_sub_genres,
        }

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
