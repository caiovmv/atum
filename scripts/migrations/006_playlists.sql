-- 006: Playlists, favoritos e contagem de reproduções.

CREATE TABLE IF NOT EXISTS playlists (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    cover_path TEXT,
    system_kind TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_playlists_system_kind ON playlists(system_kind) WHERE system_kind IS NOT NULL;

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
