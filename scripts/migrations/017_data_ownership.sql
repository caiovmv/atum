-- 017: Adiciona family_id a todas as tabelas de dados existentes.
--
-- Estratégia de backfill:
--   1. Adicionar coluna nullable
--   2. Preencher com a family_id do super_admin (usuário inicial)
--   3. Tornar NOT NULL
--
-- Requer que a migration 014 já tenha criado families e users.

-- ─── helper: family do admin inicial ─────────────────────────────────────────
-- Usado nas cláusulas de UPDATE abaixo.
-- Se não houver super_admin ainda (bootstrap), usa a primeira família existente.

DO $$
DECLARE
    admin_family_id UUID;
BEGIN
    SELECT family_id INTO admin_family_id
    FROM users
    WHERE backoffice_role = 'super_admin'
    ORDER BY created_at ASC
    LIMIT 1;

    IF admin_family_id IS NULL THEN
        SELECT id INTO admin_family_id FROM families ORDER BY created_at ASC LIMIT 1;
    END IF;

    -- downloads
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'downloads' AND column_name = 'family_id') THEN
        RAISE NOTICE 'family_id já existe em downloads, pulando';
    ELSE
        ALTER TABLE downloads ADD COLUMN family_id UUID REFERENCES families(id);
        IF admin_family_id IS NOT NULL THEN
            UPDATE downloads SET family_id = admin_family_id WHERE family_id IS NULL;
        END IF;
        ALTER TABLE downloads ALTER COLUMN family_id SET NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_downloads_family_id ON downloads (family_id);
    END IF;

    -- library_imports
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'library_imports' AND column_name = 'family_id') THEN
        RAISE NOTICE 'family_id já existe em library_imports, pulando';
    ELSE
        ALTER TABLE library_imports ADD COLUMN family_id UUID REFERENCES families(id);
        IF admin_family_id IS NOT NULL THEN
            UPDATE library_imports SET family_id = admin_family_id WHERE family_id IS NULL;
        END IF;
        ALTER TABLE library_imports ALTER COLUMN family_id SET NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_library_imports_family_id ON library_imports (family_id);
    END IF;

    -- playlists
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'playlists' AND column_name = 'family_id') THEN
        RAISE NOTICE 'family_id já existe em playlists, pulando';
    ELSE
        ALTER TABLE playlists ADD COLUMN family_id UUID REFERENCES families(id);
        IF admin_family_id IS NOT NULL THEN
            UPDATE playlists SET family_id = admin_family_id WHERE family_id IS NULL;
        END IF;
        ALTER TABLE playlists ALTER COLUMN family_id SET NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_playlists_family_id ON playlists (family_id);
    END IF;

    -- feeds
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'feeds' AND column_name = 'family_id') THEN
        RAISE NOTICE 'family_id já existe em feeds, pulando';
    ELSE
        ALTER TABLE feeds ADD COLUMN family_id UUID REFERENCES families(id);
        IF admin_family_id IS NOT NULL THEN
            UPDATE feeds SET family_id = admin_family_id WHERE family_id IS NULL;
        END IF;
        ALTER TABLE feeds ALTER COLUMN family_id SET NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_feeds_family_id ON feeds (family_id);
    END IF;

    -- wishlist
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'wishlist' AND column_name = 'family_id') THEN
        RAISE NOTICE 'family_id já existe em wishlist, pulando';
    ELSE
        ALTER TABLE wishlist ADD COLUMN family_id UUID REFERENCES families(id);
        IF admin_family_id IS NOT NULL THEN
            UPDATE wishlist SET family_id = admin_family_id WHERE family_id IS NULL;
        END IF;
        ALTER TABLE wishlist ALTER COLUMN family_id SET NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_wishlist_family_id ON wishlist (family_id);
    END IF;

    -- radio_sintonias
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'radio_sintonias' AND column_name = 'family_id') THEN
        RAISE NOTICE 'family_id já existe em radio_sintonias, pulando';
    ELSE
        ALTER TABLE radio_sintonias ADD COLUMN family_id UUID REFERENCES families(id);
        IF admin_family_id IS NOT NULL THEN
            UPDATE radio_sintonias SET family_id = admin_family_id WHERE family_id IS NULL;
        END IF;
        ALTER TABLE radio_sintonias ALTER COLUMN family_id SET NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_radio_sintonias_family_id ON radio_sintonias (family_id);
    END IF;

    -- notifications
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'notifications' AND column_name = 'family_id') THEN
        RAISE NOTICE 'family_id já existe em notifications, pulando';
    ELSE
        ALTER TABLE notifications ADD COLUMN family_id UUID REFERENCES families(id);
        IF admin_family_id IS NOT NULL THEN
            UPDATE notifications SET family_id = admin_family_id WHERE family_id IS NULL;
        END IF;
        ALTER TABLE notifications ALTER COLUMN family_id SET NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_notifications_family_id ON notifications (family_id);
    END IF;

END $$;
