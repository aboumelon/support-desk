#!/usr/bin/env bash
# Dedicated browser-test stack. Normal dev/production worker entrypoints are unchanged.
set -euo pipefail
cd "$(dirname "$0")/../apps/backend"
: "${E2E_BARRIER_DIR:?Set a private browser-test barrier directory}"
[[ "${APP_ENV:-}" == test && "${LLM_PROVIDER:-}" == fake ]] || exit 1
mkdir -p "$E2E_BARRIER_DIR"
uv run --locked --all-extras uvicorn supportdesk.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers &
api_pid=$!
uv run --locked --all-extras python -m supportdesk.workers.dispatcher &
dispatcher_pid=$!
uv run --locked --all-extras celery -A tests.e2e_worker:app worker -Q ai,ingestion --concurrency=1 --loglevel=WARNING &
worker_pid=$!
(cd ../.. && pnpm --filter @supportdesk/web dev) &
web_pid=$!
trap 'kill "$api_pid" "$dispatcher_pid" "$worker_pid" "$web_pid" 2>/dev/null || true' EXIT INT TERM
wait
