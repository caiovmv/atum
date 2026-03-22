-- 014: Auth, planos de assinatura, famílias, usuários, dispositivos, tokens e convites.
--
-- Conceitos:
--   plan      → define features e quotas do produto (editável pelo backoffice)
--   family    → unidade de assinatura multi-usuário
--   user      → pessoa física; pertence a uma família; pode ter role de backoffice
--   user_device → dispositivo registrado (para controle de limite de sessões)
--   refresh_token → tokens de renovação com hash SHA-256
--   invite_code   → convites emitidos pelo admin ou por owners de família
--   storage_addon → add-ons de storage extra ou dispositivos extras por família

-- ─── tipos enum ─────────────────────────────────────────────────────────────

CREATE TYPE user_family_role AS ENUM ('owner', 'member');
CREATE TYPE backoffice_role   AS ENUM ('super_admin', 'financial', 'support');

-- ─── planos ─────────────────────────────────────────────────────────────────

CREATE TABLE plans (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code                    TEXT        UNIQUE NOT NULL,   -- 'free' | 'family' | 'premium'
    name                    TEXT        NOT NULL,
    price_monthly_cents     INTEGER     NOT NULL DEFAULT 0,
    price_yearly_cents      INTEGER     NOT NULL DEFAULT 0,
    max_family_members      INTEGER     NOT NULL DEFAULT 1,
    max_devices_per_member  INTEGER     NOT NULL DEFAULT 1,
    base_storage_gb         INTEGER     NOT NULL DEFAULT 10,
    max_addon_storage_gb    INTEGER     NOT NULL DEFAULT 0,
    max_concurrent_downloads INTEGER   NOT NULL DEFAULT 1,
    hls_enabled             BOOLEAN     NOT NULL DEFAULT FALSE,
    ai_enabled              BOOLEAN     NOT NULL DEFAULT FALSE,
    cold_tiering_enabled    BOOLEAN     NOT NULL DEFAULT FALSE,
    trial_days              INTEGER     NOT NULL DEFAULT 0,
    stripe_product_id       TEXT,
    stripe_price_monthly_id TEXT,
    stripe_price_yearly_id  TEXT,
    is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- planos iniciais (backfill)
INSERT INTO plans (code, name, price_monthly_cents, price_yearly_cents,
                   max_family_members, max_devices_per_member, base_storage_gb,
                   max_addon_storage_gb, max_concurrent_downloads,
                   hls_enabled, ai_enabled, cold_tiering_enabled)
VALUES
    ('free',    'Free',    0,    0,     1, 1, 10,   0,   1, FALSE, FALSE, FALSE),
    ('family',  'Family',  990,  9900,  2, 3, 50,   500, 3, TRUE,  FALSE, TRUE),
    ('premium', 'Premium', 1990, 19900, 5, 3, 200,  2000,5, TRUE,  TRUE,  TRUE);

-- ─── famílias ────────────────────────────────────────────────────────────────

CREATE TABLE families (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT        NOT NULL DEFAULT '',
    plan_id    UUID        NOT NULL REFERENCES plans(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── usuários ────────────────────────────────────────────────────────────────

CREATE TABLE users (
    id               UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
    email            TEXT              UNIQUE NOT NULL,
    password_hash    TEXT              NOT NULL,
    display_name     TEXT              NOT NULL DEFAULT '',
    family_id        UUID              NOT NULL REFERENCES families(id),
    role             user_family_role  NOT NULL DEFAULT 'member',
    backoffice_role  backoffice_role,                          -- NULL = sem acesso ao backoffice
    is_active        BOOLEAN           NOT NULL DEFAULT TRUE,
    email_verified   BOOLEAN           NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    last_login_at    TIMESTAMPTZ
);

CREATE INDEX idx_users_family_id ON users (family_id);
CREATE INDEX idx_users_email     ON users (email);

-- ─── dispositivos ────────────────────────────────────────────────────────────

CREATE TABLE user_devices (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_name  TEXT        NOT NULL DEFAULT 'Unknown Device',
    user_agent   TEXT,
    ip_address   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_devices_user_id ON user_devices (user_id);

-- ─── refresh tokens ──────────────────────────────────────────────────────────

CREATE TABLE refresh_tokens (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash  TEXT        UNIQUE NOT NULL,    -- SHA-256 do token JWT
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id   UUID        REFERENCES user_devices(id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user_id    ON refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens (token_hash);

-- ─── convites ────────────────────────────────────────────────────────────────

CREATE TABLE invite_codes (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code         TEXT        UNIQUE NOT NULL,
    created_by   UUID        NOT NULL REFERENCES users(id),
    family_id    UUID        REFERENCES families(id),  -- NULL = cria nova família ao usar
    plan_id      UUID        REFERENCES plans(id),     -- sobrepõe plano ao criar família
    max_uses     INTEGER     NOT NULL DEFAULT 1,
    uses_count   INTEGER     NOT NULL DEFAULT 0,
    expires_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── add-ons de storage e dispositivos ──────────────────────────────────────

CREATE TABLE storage_addons (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id                   UUID        NOT NULL REFERENCES families(id),
    addon_type                  TEXT        NOT NULL CHECK (addon_type IN ('storage_gb', 'extra_device')),
    quantity                    INTEGER     NOT NULL CHECK (quantity > 0),
    stripe_subscription_item_id TEXT,
    active                      BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_storage_addons_family_id ON storage_addons (family_id);
