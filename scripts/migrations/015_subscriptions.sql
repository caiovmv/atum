-- 015: Assinaturas, pagamentos, códigos promocionais e log de auditoria do backoffice.

-- ─── tipos enum ─────────────────────────────────────────────────────────────

CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'canceled', 'paused');
CREATE TYPE billing_period      AS ENUM ('monthly', 'yearly');
CREATE TYPE payment_status      AS ENUM ('pending', 'succeeded', 'failed', 'refunded');

-- ─── assinaturas ─────────────────────────────────────────────────────────────

CREATE TABLE subscriptions (
    id                      UUID                PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id               UUID                NOT NULL REFERENCES families(id),
    plan_id                 UUID                NOT NULL REFERENCES plans(id),
    status                  subscription_status NOT NULL DEFAULT 'active',
    billing_period          billing_period       NOT NULL DEFAULT 'monthly',
    current_period_start    TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    current_period_end      TIMESTAMPTZ         NOT NULL,
    trial_end               TIMESTAMPTZ,
    canceled_at             TIMESTAMPTZ,
    cancel_at_period_end    BOOLEAN             NOT NULL DEFAULT FALSE,
    stripe_subscription_id  TEXT                UNIQUE,
    stripe_customer_id      TEXT,
    promo_code_id           UUID,               -- FK adicionada após criar promo_codes
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_family_id ON subscriptions (family_id);
CREATE INDEX idx_subscriptions_status    ON subscriptions (status);

-- ─── códigos promocionais ────────────────────────────────────────────────────

CREATE TABLE promo_codes (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code                  TEXT        UNIQUE NOT NULL,
    description           TEXT,
    discount_percent      INTEGER     CHECK (discount_percent BETWEEN 1 AND 100),
    discount_cents        INTEGER     CHECK (discount_cents > 0),
    max_uses              INTEGER,    -- NULL = ilimitado
    uses_count            INTEGER     NOT NULL DEFAULT 0,
    applies_to_plan_id    UUID        REFERENCES plans(id),  -- NULL = todos os planos
    stripe_coupon_id      TEXT,
    valid_from            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until           TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_discount CHECK (
        (discount_percent IS NOT NULL AND discount_cents IS NULL) OR
        (discount_percent IS NULL AND discount_cents IS NOT NULL)
    )
);

-- FK tardia: subscriptions.promo_code_id → promo_codes.id
ALTER TABLE subscriptions
    ADD CONSTRAINT fk_subscriptions_promo_code
    FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id);

-- ─── pagamentos ──────────────────────────────────────────────────────────────

CREATE TABLE payments (
    id                         UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id            UUID           NOT NULL REFERENCES subscriptions(id),
    family_id                  UUID           NOT NULL REFERENCES families(id),
    amount_cents               INTEGER        NOT NULL,
    currency                   TEXT           NOT NULL DEFAULT 'brl',
    status                     payment_status NOT NULL DEFAULT 'pending',
    stripe_payment_intent_id   TEXT           UNIQUE,
    stripe_invoice_id          TEXT           UNIQUE,
    description                TEXT,
    paid_at                    TIMESTAMPTZ,
    refunded_at                TIMESTAMPTZ,
    refund_amount_cents        INTEGER,
    created_at                 TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payments_family_id       ON payments (family_id);
CREATE INDEX idx_payments_subscription_id ON payments (subscription_id);
CREATE INDEX idx_payments_status          ON payments (status);

-- ─── log de auditoria ────────────────────────────────────────────────────────

CREATE TABLE audit_log (
    id            BIGSERIAL   PRIMARY KEY,
    actor_user_id UUID        REFERENCES users(id) ON DELETE SET NULL,
    action        TEXT        NOT NULL,   -- ex: 'plan.update', 'subscription.cancel', 'user.suspend'
    target_type   TEXT,                  -- 'user' | 'subscription' | 'plan' | 'invite_code' | ...
    target_id     TEXT,
    metadata      JSONB,
    ip_address    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_actor      ON audit_log (actor_user_id);
CREATE INDEX idx_audit_log_action     ON audit_log (action);
CREATE INDEX idx_audit_log_created_at ON audit_log (created_at DESC);
