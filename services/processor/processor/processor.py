import os, asyncio, time, asyncpg, orjson, hashlib, clickhouse_connect
from datetime import datetime
from aiokafka import AIOKafkaConsumer
from prometheus_client import start_http_server, Counter, Histogram
from .dedup import Deduper
from .geoutil import h3_from_latlon

RAW_TOPIC = os.getenv("RAW_TOPIC", "raw_events")
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "redpanda:9092")
DB_DSN = os.getenv(
    "PROCESSOR_DB_DSN",
    "postgresql://cp_user:cp_pass@postgres:5432/crisispulse"
)

incidents_inserted = Counter(
    "crisispulse_incidents_inserted_total", "Incidents inserted", ["source"]
)
dedup_dropped = Counter(
    "crisispulse_dedup_dropped_total", "Events dropped as duplicates"
)
latency_hist = Histogram(
    "crisispulse_latency_seconds", "End-to-end latency seconds",
    buckets=[0.5, 1, 2, 3, 5, 8, 13, 21, 34]
)

CREATE_SQL = '''
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
CREATE INDEX IF NOT EXISTS idx_incidents_occurred_ts ON incidents(occurred_ts);
'''

UPSERT_SQL = '''
INSERT INTO incidents
(incident_hash, source, source_id, title, body, occurred_ts, lat, lon, magnitude, severity, h3, location_text, raw, ingested_at, processed_at)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,$14,$15)
ON CONFLICT (incident_hash) DO NOTHING;
'''

def content_hash(source, source_id, title, lat, lon, occurred_ts):
    return hashlib.sha256(
        f"{source}|{source_id}|{title}|{lat}|{lon}|{occurred_ts}".encode()
    ).hexdigest()

def severity_from(payload):
    mag = payload.get("magnitude")
    return 0.3 if mag is None else max(0.0, min(1.0, (mag/10.0)))

async def ensure_db(conn):
    await conn.execute(CREATE_SQL)

async def process_loop():
    start_http_server(9000)

    # postgres connection pool
    pool = await asyncpg.create_pool(dsn=DB_DSN, min_size=1, max_size=4)
    async with pool.acquire() as conn:
        await ensure_db(conn)

    # clickhouse client
    ch_client = clickhouse_connect.get_client(
    host="clickhouse", port=8123, username="default", password="cp_pass"
    )

    # kafka consumer
    consumer = AIOKafkaConsumer(
        RAW_TOPIC,
        bootstrap_servers=KAFKA_BROKERS,
        value_deserializer=lambda v: orjson.loads(v),
        enable_auto_commit=True,
        auto_offset_reset="latest"
    )
    await consumer.start()

    deduper = Deduper(
        threshold=0.85,
        window_seconds=int(os.getenv("DEDUPE_WINDOW_MIN", "45")) * 60
    )

    try:
        async for msg in consumer:
            evt = msg.value or {}
            source = evt.get("source") or "unknown"
            payload = evt.get("payload") or {}
            title = payload.get("title") or ""
            body = payload.get("body") or ""
            source_id = payload.get("source_id") or ""
            occurred_ts = float(payload.get("occurred_ts") or time.time())
            lat = payload.get("lat")
            lon = payload.get("lon")
            location_text = payload.get("place") or payload.get("location") or ""

            drop, _ = deduper.should_drop(
                key=f"{source}:{source_id}", title=title, body=body,
                lat=lat, lon=lon, ts=occurred_ts
            )
            if drop:
                dedup_dropped.inc()
                continue

            sev = severity_from(payload)
            h3_ix = h3_from_latlon(lat, lon, 7)
            ihash = content_hash(source, source_id, title, lat, lon, occurred_ts)

            processed_at = time.time()
            ingested_at = float(evt.get("ingested_at") or processed_at)
            latency_hist.observe(processed_at - ingested_at)

            # insert into Postgres
            async with pool.acquire() as conn:
                await conn.execute(
                    UPSERT_SQL,
                    ihash, source, source_id, title, body, occurred_ts, lat, lon,
                    payload.get("magnitude"), sev, h3_ix, location_text,
                    orjson.dumps(payload).decode(),
                    ingested_at, processed_at
                )
                incidents_inserted.labels(source=source).inc()

            # insert into ClickHouse
            try:
                ch_client.insert(
                    "crisispulse.incidents",
                    [[
                        int(time.time() * 1e6),  # unique id
                        source,
                        title,
                        float(payload.get("magnitude") or 0),
                        float(sev),
                        datetime.utcfromtimestamp(occurred_ts),
                        float(lat or 0),
                        float(lon or 0)
                    ]],
                    column_names=[
                        "id", "source", "title", "magnitude", "severity",
                        "occurred_ts", "lat", "lon"
                    ]
                )
            except Exception as e:
                print(f"[WARN] ClickHouse insert failed: {e}")

    finally:
        await consumer.stop()
        await pool.close()

def main():
    asyncio.run(process_loop())

if __name__ == "__main__":
    main()
