-- 011: Campo notas (ai_notes) para armazenar o racional detalhado do LLM ao gerar AI Mix.
ALTER TABLE playlists ADD COLUMN IF NOT EXISTS ai_notes TEXT;
