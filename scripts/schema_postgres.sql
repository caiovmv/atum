-- Schema PostgreSQL para dl-torrent (compatível com schema SQLite).
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
    music_quality TEXT
);
CREATE INDEX IF NOT EXISTS ix_downloads_status ON downloads(status);

CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_search_history_created_at ON search_history(created_at DESC);

CREATE TABLE IF NOT EXISTS wishlist (
    id SERIAL PRIMARY KEY,
    term TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
