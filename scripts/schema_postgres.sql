-- Schema PostgreSQL para dl-torrent.
-- Executado na primeira conexão quando DATABASE_URL está definido.

CREATE TABLE IF NOT EXISTS feeds (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE feeds ADD COLUMN IF NOT EXISTS content_type TEXT DEFAULT 'music';

CREATE TABLE IF NOT EXISTS feed_processed (
    id SERIAL PRIMARY KEY,
    feed_id INTEGER NOT NULL REFERENCES feeds(id),
    entry_id TEXT NOT NULL,
    entry_link TEXT,
    title TEXT,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(feed_id, entry_id)
);
CREATE INDEX IF NOT EXISTS ix_feed_processed_feed_id ON feed_processed(feed_id);

CREATE TABLE IF NOT EXISTS feed_pending (
    id SERIAL PRIMARY KEY,
    feed_id INTEGER NOT NULL REFERENCES feeds(id),
    entry_id TEXT NOT NULL,
    title TEXT,
    link TEXT,
    quality_label TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(feed_id, entry_id)
);
CREATE INDEX IF NOT EXISTS ix_feed_pending_feed_id ON feed_pending(feed_id);

CREATE TABLE IF NOT EXISTS downloads (
    id SERIAL PRIMARY KEY,
    magnet TEXT NOT NULL,
    name TEXT,
    save_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress REAL DEFAULT 0,
    pid INTEGER,
    error_message TEXT,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    num_seeds INTEGER,
    num_peers INTEGER,
    download_speed_bps INTEGER,
    total_bytes BIGINT,
    downloaded_bytes BIGINT,
    eta_seconds REAL,
    content_path TEXT,
    content_type TEXT,
    cover_path_small TEXT,
    cover_path_large TEXT,
    year INTEGER,
    video_quality_label TEXT,
    audio_codec TEXT,
    music_quality TEXT,
    excluded_file_indices JSONB,
    torrent_files JSONB
);
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS excluded_file_indices JSONB;
ALTER TABLE downloads ADD COLUMN IF NOT EXISTS torrent_files JSONB;
CREATE INDEX IF NOT EXISTS ix_downloads_status ON downloads(status);

CREATE TABLE IF NOT EXISTS wishlist (
    id SERIAL PRIMARY KEY,
    term TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    payload JSONB,
    read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_notifications_read_created ON notifications(read, created_at DESC);

-- Itens da biblioteca descobertos pelo sync (pastas já existentes em Library Music/Videos).
CREATE TABLE IF NOT EXISTS library_imports (
    id SERIAL PRIMARY KEY,
    content_path TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL DEFAULT 'music',
    name TEXT NOT NULL,
    year INTEGER,
    metadata_json JSONB,
    cover_path_small TEXT,
    cover_path_large TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_library_imports_content_path ON library_imports(content_path);
CREATE INDEX IF NOT EXISTS ix_library_imports_content_type ON library_imports(content_type);
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS artist TEXT;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS album TEXT;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS genre TEXT;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;

-- Rádio: sintonias (presets) com regras de include/exclude.
CREATE TABLE IF NOT EXISTS radio_sintonias (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE radio_sintonias ADD COLUMN IF NOT EXISTS cover_path TEXT;

CREATE TABLE IF NOT EXISTS radio_sintonia_rules (
    id SERIAL PRIMARY KEY,
    sintonia_id INTEGER NOT NULL REFERENCES radio_sintonias(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('include', 'exclude')),
    "type" TEXT NOT NULL CHECK ("type" IN ('content_type', 'genre', 'artist', 'tag', 'item')),
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_radio_sintonia_rules_sintonia_id ON radio_sintonia_rules(sintonia_id);

-- Versionamento: tabela que registra quais migrations (scripts/migrations/*.sql) já foram aplicadas.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
