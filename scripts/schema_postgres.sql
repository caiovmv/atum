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
CREATE INDEX IF NOT EXISTS ix_feed_pending_created_at ON feed_pending(created_at DESC);

CREATE TABLE IF NOT EXISTS downloads (
    id SERIAL PRIMARY KEY,
    magnet TEXT NOT NULL,
    torrent_url TEXT,
    name TEXT,
    save_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'downloading', 'completed', 'failed', 'paused')),
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
    content_type TEXT CHECK (content_type IS NULL OR content_type IN ('music', 'movies', 'tv')),
    cover_path_small TEXT,
    cover_path_large TEXT,
    year INTEGER,
    video_quality_label TEXT,
    audio_codec TEXT,
    music_quality TEXT,
    excluded_file_indices JSONB,
    torrent_files JSONB,
    artist TEXT,
    album TEXT,
    genre TEXT,
    library_path TEXT,
    post_processed BOOLEAN DEFAULT FALSE,
    tmdb_id INTEGER,
    imdb_id TEXT,
    bpm REAL,
    musical_key TEXT,
    energy REAL,
    danceability REAL,
    valence REAL,
    loudness_db REAL,
    replaygain_db REAL,
    musicbrainz_id TEXT,
    sub_genres TEXT[],
    moods TEXT[],
    descriptors TEXT[],
    record_label TEXT,
    release_type TEXT,
    overview TEXT,
    vote_average REAL,
    runtime_minutes INTEGER,
    backdrop_path TEXT,
    original_title TEXT,
    tmdb_genres TEXT[],
    enriched_at TIMESTAMPTZ,
    enrichment_sources TEXT[],
    enrichment_error TEXT,
    tags JSONB DEFAULT '[]'::jsonb,
    search_vector TSVECTOR
) WITH (fillfactor = 70, autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);
CREATE INDEX IF NOT EXISTS ix_downloads_status ON downloads(status);
CREATE INDEX IF NOT EXISTS ix_downloads_content_type_status ON downloads(content_type, status);
CREATE INDEX IF NOT EXISTS ix_downloads_updated_at ON downloads(updated_at DESC);
-- ix_downloads_artist, ix_downloads_search_vector, ix_downloads_pending_enrichment ficam nas migrations 008 e 009
CREATE INDEX IF NOT EXISTS ix_downloads_content_type_name ON downloads(content_type, name);

CREATE TABLE IF NOT EXISTS wishlist (
    id SERIAL PRIMARY KEY,
    term TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_wishlist_created_at ON wishlist(created_at DESC);

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
    content_type TEXT NOT NULL DEFAULT 'music' CHECK (content_type IN ('music', 'movies', 'tv')),
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
CREATE INDEX IF NOT EXISTS ix_library_imports_content_type_created ON library_imports(content_type, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_library_imports_content_type_name ON library_imports(content_type, name);
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS artist TEXT;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS album TEXT;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS genre TEXT;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;
CREATE INDEX IF NOT EXISTS ix_library_imports_search_vector ON library_imports USING GIN (search_vector);

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

-- Playlists (favoritos, mais tocadas, sintonias dinâmicas, AI mixes e playlists do usuário).
CREATE TABLE IF NOT EXISTS playlists (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    cover_path TEXT,
    system_kind TEXT,
    kind TEXT NOT NULL DEFAULT 'static',
    rules JSONB,
    ai_prompt TEXT,
    ai_notes TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_playlists_system_kind ON playlists(system_kind) WHERE system_kind IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_playlists_kind ON playlists(kind);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('download', 'import')),
    item_id INTEGER NOT NULL,
    file_index INTEGER NOT NULL DEFAULT 0,
    file_name TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(playlist_id, source, item_id, file_index)
);
CREATE INDEX IF NOT EXISTS ix_playlist_tracks_playlist_id ON playlist_tracks(playlist_id);
CREATE INDEX IF NOT EXISTS ix_playlist_tracks_position ON playlist_tracks(playlist_id, position);

CREATE TABLE IF NOT EXISTS track_play_counts (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN ('download', 'import')),
    item_id INTEGER NOT NULL,
    file_index INTEGER NOT NULL DEFAULT 0,
    play_count INTEGER NOT NULL DEFAULT 0,
    last_played_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, item_id, file_index)
);
CREATE INDEX IF NOT EXISTS ix_track_play_counts_top ON track_play_counts(play_count DESC);

INSERT INTO playlists (name, system_kind) VALUES ('Favoritos', 'favorites') ON CONFLICT DO NOTHING;
INSERT INTO playlists (name, system_kind) VALUES ('Mais Tocadas', 'most_played') ON CONFLICT DO NOTHING;

-- Versionamento: tabela que registra quais migrations (scripts/migrations/*.sql) já foram aplicadas.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
