-- 016: Jobs HLS (daemon isolado), posições de reprodução, fila de sync cloud e tier de storage.

-- ─── tipos enum ─────────────────────────────────────────────────────────────

CREATE TYPE hls_strategy   AS ENUM ('on_demand', 'automatic', 'lru');
CREATE TYPE hls_job_status AS ENUM ('pending', 'processing', 'done', 'failed', 'evicted');
CREATE TYPE sync_operation AS ENUM ('upload_cold', 'download_warm', 'delete_local', 'prefetch');
CREATE TYPE storage_tier   AS ENUM ('local', 'cloud', 'both', 'offline_only');

-- ─── jobs HLS ────────────────────────────────────────────────────────────────
-- Fila de transcodificação gerenciada pelo hls-daemon (fora da API).
-- A API cria/consulta jobs; o daemon processa e faz upload para MinIO.

CREATE TABLE hls_jobs (
    id               UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id        UUID           NOT NULL REFERENCES families(id),
    library_id       INTEGER        NOT NULL,
    file_index       INTEGER        NOT NULL DEFAULT 0,
    status           hls_job_status NOT NULL DEFAULT 'pending',
    strategy         hls_strategy   NOT NULL DEFAULT 'on_demand',
    progress_pct     SMALLINT       NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    minio_prefix     TEXT,          -- s3://loombeat-hls/{family_id}/{lib_id}_{idx}/
    error_msg        TEXT,
    last_accessed_at TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    created_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    UNIQUE (family_id, library_id, file_index)
);

CREATE INDEX idx_hls_jobs_status         ON hls_jobs (status);
CREATE INDEX idx_hls_jobs_family_id      ON hls_jobs (family_id);
CREATE INDEX idx_hls_jobs_last_accessed  ON hls_jobs (last_accessed_at);

-- ─── posições de reprodução (sync cross-device) ───────────────────────────────

CREATE TABLE play_positions (
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    library_id  INTEGER     NOT NULL,
    position_sec REAL       NOT NULL DEFAULT 0 CHECK (position_sec >= 0),
    duration_sec REAL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, library_id)
);

CREATE INDEX idx_play_positions_user_id ON play_positions (user_id);

-- ─── fila de sincronização cloud ─────────────────────────────────────────────

CREATE TABLE cloud_sync_queue (
    id           BIGSERIAL    PRIMARY KEY,
    family_id    UUID         NOT NULL REFERENCES families(id),
    library_id   INTEGER      NOT NULL,
    operation    sync_operation NOT NULL,
    minio_key    TEXT,
    status       TEXT         NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    attempts     SMALLINT     NOT NULL DEFAULT 0,
    error_msg    TEXT,
    scheduled_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cloud_sync_queue_status      ON cloud_sync_queue (status, scheduled_at);
CREATE INDEX idx_cloud_sync_queue_family_id   ON cloud_sync_queue (family_id);

-- ─── tier de storage em library_imports ──────────────────────────────────────

ALTER TABLE library_imports
    ADD COLUMN IF NOT EXISTS storage_tier    storage_tier NOT NULL DEFAULT 'local',
    ADD COLUMN IF NOT EXISTS minio_key       TEXT,
    ADD COLUMN IF NOT EXISTS last_played_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS local_size_bytes BIGINT;

CREATE INDEX idx_library_imports_storage_tier   ON library_imports (storage_tier);
CREATE INDEX idx_library_imports_last_played_at ON library_imports (last_played_at NULLS LAST);
