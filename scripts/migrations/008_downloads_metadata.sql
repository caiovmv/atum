-- Metadados extraídos de downloads concluídos para facets unificados na biblioteca.
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS artist TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS album TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS genre TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS library_path TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS post_processed BOOLEAN DEFAULT FALSE;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS tmdb_id INTEGER;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS imdb_id TEXT;

CREATE INDEX IF NOT EXISTS ix_downloads_artist ON downloads(artist) WHERE artist IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_downloads_content_type_name ON downloads(content_type, name);
