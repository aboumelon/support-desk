#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/backend"
export DATABASE_URL=postgresql+psycopg://supportdesk:local-development-only@127.0.0.1:55432/supportdesk_benchmark
export REDIS_URL=redis://127.0.0.1:56379/14
export UV_CACHE_DIR=/tmp/supportdesk-uv-cache
uv run --all-extras python -m supportdesk.cli.prepare_benchmark
uv run --all-extras uvicorn supportdesk.main:create_app --factory --host 127.0.0.1 --port 19001 --no-access-log --log-level warning &
first=$!
uv run --all-extras uvicorn supportdesk.main:create_app --factory --host 127.0.0.1 --port 19002 --no-access-log --log-level warning &
second=$!
uv run --all-extras python -m supportdesk.workers.dispatcher &
dispatcher=$!
trap 'kill "$first" "$second" "$dispatcher" 2>/dev/null || true' EXIT INT TERM
wait
