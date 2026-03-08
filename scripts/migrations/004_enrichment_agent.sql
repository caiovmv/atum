-- Enrichment agent: novas colunas em library_imports para metadata enriquecida.

-- Música: análise de áudio (essentia / Spotify Audio Features)
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS bpm real;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS musical_key text;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS energy real;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS danceability real;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS valence real;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS loudness_db real;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS replaygain_db real;

-- Música: metadata externa (MusicBrainz, Last.fm, LLM)
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS musicbrainz_id text;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS sub_genres text[];
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS moods text[];
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS descriptors text[];
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS record_label text;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS release_type text;

-- Vídeo: campos TMDB ricos (já vêm da API mas não eram salvos)
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS overview text;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS vote_average real;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS runtime_minutes integer;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS backdrop_path text;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS original_title text;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS tmdb_genres text[];

-- Controle do enrichment
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS enriched_at timestamptz;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS enrichment_sources text[];
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS enrichment_error text;

-- Índice parcial para list_pending_enrichment (itens pendentes ou com erro antigo)
CREATE INDEX IF NOT EXISTS ix_library_imports_pending_enrichment
    ON library_imports (created_at)
    WHERE enriched_at IS NULL OR enrichment_error IS NOT NULL;
