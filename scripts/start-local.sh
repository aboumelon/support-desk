#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
project_root="$PWD"
mkdir -p .local
docker compose -f compose.yaml -f compose.dev.yaml up -d --wait postgres redis
if [ -f .local/dev.pid ]; then
  demo_pid=$(cat .local/dev.pid)
  case "$demo_pid" in
    ''|*[!0-9]*) echo 'Invalid local supervisor PID; refusing to signal it.' >&2; exit 1;;
  esac
  # A stale PID file must never authorize signalling an unrelated process group.
  if [ -r "/proc/$demo_pid/cmdline" ]; then
    command_line=$(tr '\0' ' ' <"/proc/$demo_pid/cmdline")
    process_directory=$(readlink "/proc/$demo_pid/cwd" || true)
    process_group=$(ps -o pgid= -p "$demo_pid" | tr -d ' ')
    if [ "$command_line" != 'bash scripts/dev.sh ' ] || [ "$process_directory" != "$project_root/apps/backend" ] || [ "$process_group" != "$demo_pid" ]; then
      echo 'PID file points to a different process; inspect .local/dev.pid before restarting.' >&2
      exit 1
    fi
    kill -TERM -- "-$demo_pid"
    for attempt in $(seq 1 50); do
      if ! kill -0 "$demo_pid" 2>/dev/null; then break; fi
      sleep 0.2
    done
  fi
fi
setsid nohup bash scripts/dev.sh >.local/dev.log 2>&1 </dev/null &
printf '%s\n' "$!" >.local/dev.pid
export UV_CACHE_DIR=/tmp/supportdesk-uv-cache
uv run --locked --project apps/backend --all-extras python -m supportdesk.cli.wait_demo
printf '%s\n' 'SupportDesk is running at http://localhost:5173'
