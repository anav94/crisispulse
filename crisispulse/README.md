

# CrisisPulse

[![CI](https://github.com/anav94/crisispulse/actions/workflows/ci.yml/badge.svg)](https://github.com/anav94/crisispulse/actions/workflows/ci.yml)

Run locally on Docker (M2-friendly). Map + table, live updates, metrics.


Quick start:
1) `cp .env.example .env`
2) `docker compose up -d --build`
3) `docker compose exec api bash -lc "python -m app.db_init"`
4) UI http://localhost:8000 • Prometheus http://localhost:9090 • Grafana http://localhost:3000 (admin/admin)
