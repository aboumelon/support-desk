#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Start isolated benchmark API replicas and dispatcher before invoking this script.
docker run --rm --network host --user "$(id -u):$(id -g)" -v "$PWD:/workspace" -w /workspace/scripts -e DURATION_SECONDS="${DURATION_SECONDS:-600}" grafana/k6:1.0.0 run --summary-export=/workspace/.local/benchmark-summary.json benchmark-realtime.js
