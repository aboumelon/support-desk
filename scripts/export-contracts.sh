#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
(cd apps/backend && UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked python -m supportdesk.cli.export_contracts)
pnpm exec openapi-typescript contracts/openapi.json -o packages/api-client/src/generated/http.d.ts
pnpm exec json2ts contracts/realtime.schema.json packages/api-client/src/generated/realtime.d.ts
cp contracts/realtime.schema.json packages/api-client/src/generated/realtime.schema.json
