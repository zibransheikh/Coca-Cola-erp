#!/bin/sh
set -e

echo "[entrypoint] starting, PORT=${PORT:-8000}"
echo "[entrypoint] running migrations..."
alembic upgrade head
echo "[entrypoint] migrations done, starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
