#!/bin/sh
set -eu

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI on port ${PORT:-10000}..."
exec fastapi run app/main.py --host 0.0.0.0 --port "${PORT:-10000}"
