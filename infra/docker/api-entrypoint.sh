#!/bin/sh
set -eu
cd /app/apps/api

# Cloud hosts (Render, Railway, Fly) assign the port at runtime and expect the
# process to bind it. Compose has no PORT set, so 8000 stays the local default.
PORT="${PORT:-8000}"

# Alembic migrations target Postgres (they use JSONB), and the app creates its
# own tables on SQLite via init_db(). Running them against the SQLite default
# would fail the container on start, so only migrate when actually on Postgres.
case "${DATABASE_URL:-}" in
  postgres*|postgresql*)
    echo "Postgres detected — running migrations"
    alembic upgrade head
    ;;
  *)
    echo "No Postgres URL — skipping migrations (tables are created at startup)"
    ;;
esac

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
