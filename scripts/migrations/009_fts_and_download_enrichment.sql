-- Full-Text Search (tsvector) em library_imports e downloads
-- + colunas de enrichment na tabela downloads

-- ===== Downloads: colunas de enrichment (mesmas da library_imports) =====
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS bpm REAL;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS musical_key TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS energy REAL;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS danceability REAL;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS valence REAL;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS loudness_db REAL;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS replaygain_db REAL;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS musicbrainz_id TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS sub_genres TEXT[];
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS moods TEXT[];
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS descriptors TEXT[];
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS record_label TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS release_type TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS overview TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS vote_average REAL;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS runtime_minutes INTEGER;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS backdrop_path TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS original_title TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS tmdb_genres TEXT[];
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS enrichment_sources TEXT[];
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS enrichment_error TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;

-- ===== FTS: library_imports =====
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

CREATE OR REPLACE FUNCTION library_imports_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.artist, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.album, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(NEW.genre, '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.overview, '')), 'D') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.moods, ' '), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.sub_genres, ' '), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.descriptors, ' '), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.tmdb_genres, ' '), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.record_label, '')), 'D') ||
        setweight(to_tsvector('simple', COALESCE(NEW.original_title, '')), 'D');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_library_imports_search_vector ON library_imports;
CREATE TRIGGER trg_library_imports_search_vector
    BEFORE INSERT OR UPDATE ON library_imports
    FOR EACH ROW EXECUTE FUNCTION library_imports_search_vector_update();

CREATE INDEX IF NOT EXISTS ix_library_imports_search_vector
    ON library_imports USING GIN (search_vector);

-- Populate search_vector for existing rows
UPDATE library_imports SET updated_at = updated_at WHERE search_vector IS NULL;

-- ===== FTS: downloads =====
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

CREATE OR REPLACE FUNCTION downloads_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.artist, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.album, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(NEW.genre, '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.overview, '')), 'D') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.moods, ' '), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.sub_genres, ' '), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.descriptors, ' '), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.tmdb_genres, ' '), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.record_label, '')), 'D') ||
        setweight(to_tsvector('simple', COALESCE(NEW.original_title, '')), 'D');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_downloads_search_vector ON downloads;
CREATE TRIGGER trg_downloads_search_vector
    BEFORE INSERT OR UPDATE ON downloads
    FOR EACH ROW EXECUTE FUNCTION downloads_search_vector_update();

CREATE INDEX IF NOT EXISTS ix_downloads_search_vector
    ON downloads USING GIN (search_vector);

-- Populate search_vector for existing rows
UPDATE downloads SET updated_at = updated_at WHERE search_vector IS NULL;

-- Index for pending enrichment on downloads (music completed without enrichment)
CREATE INDEX IF NOT EXISTS ix_downloads_pending_enrichment
    ON downloads (added_at)
    WHERE status = 'completed' AND (enriched_at IS NULL OR enrichment_error IS NOT NULL);
