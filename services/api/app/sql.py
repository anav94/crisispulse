CREATE_SQL = """
CREATE TABLE IF NOT EXISTS incidents (
    id BIGSERIAL PRIMARY KEY,
    incident_hash TEXT UNIQUE,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT,
    body TEXT,
    occurred_ts DOUBLE PRECISION,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    magnitude DOUBLE PRECISION,
    severity DOUBLE PRECISION,
    h3 TEXT,
    location_text TEXT,
    raw JSONB,
    ingested_at DOUBLE PRECISION,
    processed_at DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC);
"""
