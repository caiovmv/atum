-- 012: Adiciona content_type 'concerts' para filtrar concertos na biblioteca.
-- Altera CHECK constraints em library_imports e downloads.

ALTER TABLE downloads DROP CONSTRAINT IF EXISTS ck_downloads_content_type;
ALTER TABLE downloads ADD CONSTRAINT ck_downloads_content_type
    CHECK (content_type IS NULL OR content_type IN ('music', 'movies', 'tv', 'concerts'));

ALTER TABLE library_imports DROP CONSTRAINT IF EXISTS ck_library_imports_content_type;
ALTER TABLE library_imports ADD CONSTRAINT ck_library_imports_content_type
    CHECK (content_type IN ('music', 'movies', 'tv', 'concerts'));
