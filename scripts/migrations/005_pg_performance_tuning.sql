-- Performance: FILLFACTOR para HOT updates na tabela downloads (reduz bloat de update_progress)
ALTER TABLE downloads SET (fillfactor = 70, autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);

-- Índices adicionais para queries comuns
CREATE INDEX IF NOT EXISTS ix_downloads_content_type_status ON downloads(content_type, status);
CREATE INDEX IF NOT EXISTS ix_downloads_updated_at ON downloads(updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_feed_pending_created_at ON feed_pending(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_library_imports_content_type_created ON library_imports(content_type, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_library_imports_content_type_name ON library_imports(content_type, name);
CREATE INDEX IF NOT EXISTS ix_wishlist_created_at ON wishlist(created_at DESC);

-- CHECK constraints para integridade de dados (safe: ignora se já existe)
DO $$
BEGIN
    ALTER TABLE downloads ADD CONSTRAINT ck_downloads_status
        CHECK (status IN ('queued', 'downloading', 'completed', 'failed', 'paused')) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE downloads ADD CONSTRAINT ck_downloads_content_type
        CHECK (content_type IS NULL OR content_type IN ('music', 'movies', 'tv')) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    ALTER TABLE library_imports ADD CONSTRAINT ck_library_imports_content_type
        CHECK (content_type IN ('music', 'movies', 'tv')) NOT VALID;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE downloads VALIDATE CONSTRAINT ck_downloads_status;
ALTER TABLE downloads VALIDATE CONSTRAINT ck_downloads_content_type;
ALTER TABLE library_imports VALIDATE CONSTRAINT ck_library_imports_content_type
