#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
before=$(mktemp)
after=$(mktemp)
trap 'rm -f "$before" "$after"' EXIT
sha256sum contracts/*.json packages/api-client/src/generated/* apps/web/src/generated/* > "$before"
bash scripts/export-contracts.sh
sha256sum contracts/*.json packages/api-client/src/generated/* apps/web/src/generated/* > "$after"
diff -u "$before" "$after"
