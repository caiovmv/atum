-- 013: user_edited_at (bloqueia re-enriquecimento) e cover_source (origem da capa).
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS user_edited_at TIMESTAMPTZ;
ALTER TABLE library_imports ADD COLUMN IF NOT EXISTS cover_source TEXT;
