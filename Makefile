SHELL := /bin/bash
export COMPOSE_PROJECT_NAME ?= crisispulse
up:; docker compose up -d --build
down:; docker compose down -v
logs:; docker compose logs -f --tail=200
ps:; docker compose ps
init-db:; docker compose exec api bash -lc "python -m app.db_init"
seed:; docker compose run --rm collectors python -m collectors.synthetic --count 50 --burst
test:; docker compose run --rm processor pytest -q
