#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .local
recovery_name="supportdesk-recovery-$$"
service_pid=''
outage_pid=''
cleanup() {
  if [ -n "$outage_pid" ]; then kill "$outage_pid" 2>/dev/null || true; fi
  if [ -n "$service_pid" ]; then kill -TERM -- "-$service_pid" 2>/dev/null || true; fi
  docker rm -f "$recovery_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
docker run -d --name "$recovery_name" -p 127.0.0.1:56381:6379 redis:8.0.2-alpine@sha256:48501c5ad00d5563bc30c075c7bcef41d7d98de3e9a1e6c752068c66f0a8463b >/dev/null
BENCHMARK_REDIS_URL=redis://127.0.0.1:56381/14 setsid bash scripts/benchmark-services.sh >.local/recovery-services.log 2>&1 &
service_pid=$!
for attempt in $(seq 1 100); do
  if curl --noproxy '*' -fsS http://127.0.0.1:19001/api/v1/health/ready >/dev/null && curl --noproxy '*' -fsS http://127.0.0.1:19002/api/v1/health/ready >/dev/null; then break; fi
  sleep 0.2
done
(
  sleep 30
  docker stop -t 0 "$recovery_name" >/dev/null
  sleep 5
  docker start "$recovery_name" >/dev/null
) &
outage_pid=$!
status=0
DURATION_SECONDS="${RECOVERY_DURATION_SECONDS:-600}" RECOVERY=1 bash scripts/run-benchmark.sh || status=$?
cp .local/benchmark-summary.json docs/evidence/benchmark-recovery.json
wait "$outage_pid"
apps/backend/.venv/bin/python - <<'PY'
import json
from pathlib import Path

report = json.loads(Path('docs/evidence/benchmark-recovery.json').read_text())
if report['metrics']['checks']['fails']:
    raise SystemExit('A client connection, send or acknowledged-delivery check failed')
PY
exit "$status"
