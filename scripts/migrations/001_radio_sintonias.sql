-- Migration: tabelas de Rádio (sintonias e regras).
-- Executado após o schema principal em toda nova conexão (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS radio_sintonias (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS radio_sintonia_rules (
    id SERIAL PRIMARY KEY,
    sintonia_id INTEGER NOT NULL REFERENCES radio_sintonias(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('include', 'exclude')),
    "type" TEXT NOT NULL CHECK ("type" IN ('content_type', 'genre', 'artist', 'tag', 'item')),
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_radio_sintonia_rules_sintonia_id ON radio_sintonia_rules(sintonia_id);
