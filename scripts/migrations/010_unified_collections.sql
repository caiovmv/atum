-- 010: Coleções unificadas — absorve sintonias e smart queue como tipos de playlist.

-- Novas colunas na tabela playlists
ALTER TABLE playlists ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'static';
-- 'static' = playlist normal, 'dynamic_rules' = sintonia, 'dynamic_ai' = AI mix

ALTER TABLE playlists ADD COLUMN IF NOT EXISTS rules JSONB;
-- Para kind='dynamic_rules': [{kind:"include",type:"genre",value:"rock"}, ...]

ALTER TABLE playlists ADD COLUMN IF NOT EXISTS ai_prompt TEXT;
-- Para kind='dynamic_ai': o prompt original do usuario

ALTER TABLE playlists ADD COLUMN IF NOT EXISTS description TEXT;
-- Descricao opcional (AI pode preencher automaticamente)

CREATE INDEX IF NOT EXISTS ix_playlists_kind ON playlists(kind);

-- Migrar sintonias existentes para playlists (apenas se tabelas existirem)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'radio_sintonias') THEN
    INSERT INTO playlists (name, kind, rules, cover_path, created_at)
    SELECT
        s.name,
        'dynamic_rules',
        (
            SELECT COALESCE(json_agg(json_build_object('kind', r.kind, 'type', r."type", 'value', r.value)), '[]'::json)
            FROM radio_sintonia_rules r
            WHERE r.sintonia_id = s.id
        )::jsonb,
        s.cover_path,
        s.created_at
    FROM radio_sintonias s
    WHERE NOT EXISTS (
        SELECT 1 FROM playlists p
        WHERE p.name = s.name AND p.kind = 'dynamic_rules'
    );
  END IF;
END $$;
