#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Start isolated benchmark API replicas and dispatcher before invoking this script.
docker run --rm --network host --user "$(id -u):$(id -g)" -v "$PWD:/workspace" -w /workspace/scripts -e DURATION_SECONDS="${DURATION_SECONDS:-600}" -e RECOVERY="${RECOVERY:-0}" grafana/k6:1.0.0@sha256:f21270290d702cbf0a7d6ba5d7ed100b63bcb233b558b885ed787547b3488279 run --summary-export=/workspace/.local/benchmark-summary.json benchmark-realtime.js
