#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/backend"
export UV_CACHE_DIR=/tmp/supportdesk-uv-cache
uv run --all-extras uvicorn supportdesk.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log &
api_pid=$!
uv run --all-extras python -m supportdesk.workers.dispatcher &
dispatcher_pid=$!
uv run --all-extras celery -A supportdesk.workers.celery_app:app worker -Q ai,ingestion --concurrency=1 --loglevel=WARNING &
worker_pid=$!
(cd ../.. && pnpm --filter @supportdesk/web dev) &
web_pid=$!
trap 'kill "$api_pid" "$dispatcher_pid" "$worker_pid" "$web_pid" 2>/dev/null || true' EXIT INT TERM
wait
