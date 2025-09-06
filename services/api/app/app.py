import os, asyncio, json, datetime
import asyncpg
import httpx

from fastapi import FastAPI, Query, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .db import get_pool
from .sql import CREATE_SQL

app = FastAPI(
    title="CrisisPulse API",
    description="Real-time crisis intelligence pipeline (API + Web UI)",
    version="1.0.0"
)

# --------------------
# Startup / Shutdown
# --------------------
@app.on_event("startup")
async def startup():
    app.state.pool = await get_pool()
    async with app.state.pool.acquire() as conn:
        await conn.execute(CREATE_SQL)

@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()

# --------------------
# Health Endpoints
# --------------------
@app.get("/health", status_code=status.HTTP_200_OK)
async def healthcheck():
    status_report = {"status": "ok"}

    # Postgres check
    try:
        conn = await asyncpg.connect(
            dsn=os.getenv("PROCESSOR_DB_DSN",
                          "postgresql://cp_user:cp_pass@postgres:5432/crisispulse")
        )
        await conn.close()
        status_report["postgres"] = True
    except Exception:
        status_report["postgres"] = False

    # ClickHouse check
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://clickhouse:8123/ping")
            status_report["clickhouse"] = r.text.strip() == "Ok."
    except Exception:
        status_report["clickhouse"] = False

    return status_report

@app.get("/healthz")
async def healthz():
    return {"ok": True}

# --------------------
# Metrics
# --------------------
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# --------------------
# API Routes
# --------------------
@app.get("/api/incidents")
async def list_incidents(limit: int = Query(200, le=500)):
    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, source, source_id, title, body, occurred_ts, lat, lon,
                   magnitude, severity, h3, location_text, created_at
            FROM incidents
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)
        return [dict(r) for r in rows]

from fastapi.responses import StreamingResponse

@app.get("/stream")
async def stream(last_id: int = 0):
    async def event_gen():
        nonlocal last_id
        while True:
            async with app.state.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, source, title, occurred_ts, lat, lon, magnitude, severity, location_text, created_at
                    FROM incidents WHERE id > $1 ORDER BY id ASC LIMIT 200
                """, last_id)
                for r in rows:
                    eid = r["id"]
                    data = {}
                    for k, v in r.items():
                        if isinstance(v, datetime.datetime):
                            data[k] = v.isoformat()  # <-- convert datetime → string
                        else:
                            data[k] = v
                    yield f"id: {eid}\nevent: incident\ndata: {json.dumps(data)}\n\n"
                    last_id = eid
            await asyncio.sleep(2.0)
    return StreamingResponse(event_gen(), media_type="text/event-stream")

# --------------------
# Static UI
# --------------------
@app.get("/")
async def index():
    return FileResponse("app/static/index.html")

@app.get("/static/{path:path}")
async def static(path: str):
    return FileResponse(f"app/static/{path}")