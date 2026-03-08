-- Settings em runtime (overrides do .env, editáveis pela interface web).
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Enriquecimento TMDB/IMDB nos downloads
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS tmdb_id INTEGER;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS imdb_id TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS library_path TEXT;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS post_processed BOOLEAN DEFAULT FALSE;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS previous_content_path TEXT;

-- Enriquecimento TMDB/IMDB nos library_imports
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS tmdb_id INTEGER;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS imdb_id TEXT;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS quality_label TEXT;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS previous_content_path TEXT;
