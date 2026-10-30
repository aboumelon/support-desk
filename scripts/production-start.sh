#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
env_file="${PORTFOLIO_ENV_FILE:-.env.production}"
if [ ! -f "$env_file" ]; then
  echo 'Create a private environment file from deploy/production.env.example first.' >&2
  exit 1
fi
compose=(docker compose --env-file "$env_file" -f deploy/compose.production.yaml)
"${compose[@]}" config --quiet
"${compose[@]}" build api worker gateway
"${compose[@]}" up -d --wait --wait-timeout 90 postgres redis
"${compose[@]}" run --rm --no-deps migrate
"${compose[@]}" run --rm --no-deps roles
"${compose[@]}" run --rm --no-deps model-init
"${compose[@]}" run --rm --no-deps seed
"${compose[@]}" up -d --wait --wait-timeout 180 api dispatcher worker retention
"${compose[@]}" run --rm --no-deps wait-knowledge
"${compose[@]}" up -d --wait --wait-timeout 90 gateway
printf '%s\n' 'Portfolio stack is ready. Verify the configured HTTPS origin before public routing.'
