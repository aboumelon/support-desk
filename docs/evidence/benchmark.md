# Local two-API benchmark, 2026-10-29

Environment: Linux development host, 4 available CPUs, approximately 7 GiB physical RAM;
PostgreSQL 17/pgvector 0.8.0, Redis 8.0.2, Python 3.13.14, two Uvicorn API processes,
separate dispatcher, no LLM work in the benchmark workspace. Other local development
processes were present; this is not a dedicated production-capacity measurement.

Command: `bash scripts/run-benchmark.sh`, after starting the isolated benchmark services.
k6 image: `grafana/k6:1.0.0` (digest `sha256:f21270290d702cbf0a7d6ba5d7ed100b63bcb233b558b885ed787547b3488279`).
The fixture command refuses any database not ending in `_benchmark`. Credentials remain
in ignored `.local/benchmark-sessions.json`; no credential is included in this report.

The final source-checkpoint run (`f4976cceb2e7698f647f3136f98528f80069965f`) used 200 clients split across two API instances,
a short 20-message/second burst and a staggered reconnect wave. Results:

| Signal | Measured |
| --- | --- |
| HTTP message commands | 3,192 |
| Observed HTTP command rate including burst | 5.30/s |
| Message commit p95 | 80.26 ms |
| Message delivery p95 | 416.00 ms |
| Message command failures | 0 |
| WebSocket sessions including reconnects | 400 |
| k6 checks | 3,592 passed, 0 failed |

Both configured p95 thresholds and the zero-failure gate passed. Delivery is measured
from a client timestamp inserted before the REST send, so it includes commit latency.
Maximum observed commit/delivery times were about 2.3/5.9 seconds; passing p95 does not
imply every request met the target. The original failed run and short intermediate run
are retained as JSON next to `benchmark-final.json`; the earlier corrected full run is `benchmark-initial-corrected.json`. The final console report is `benchmark-final-console.txt`.

Failure diagnosis and correction: workspace-wide notifications caused unrelated replay
queries, a one-row/250ms loop could dispatch fewer events than the requested send rate,
and message quota checking acquired another DB connection while holding the first.
The implementation now filters notification subscriptions, drains outbox batches and
checks quotas within the message transaction. Final dispatcher polling is 250 ms.

Separate reliability tests exercise two actual API processes, a lost last notification,
real Redis outage/restart and an actual Celery SIGKILL followed by lease expiry and
queue reconstruction. Recovery/load behavior beyond the tested scenario is not a
high-availability or production capacity guarantee.

## Additional outage measurements

`bash scripts/run-recovery-benchmark.sh` provisions its own Redis on loopback 56381,
two API processes and 200 clients. It stops Redis for five seconds, reconnects all
clients and checks that every acknowledged message has arrived. The short runs retained
in `benchmark-recovery-before-presence.json` and `benchmark-recovery-short-with-tests.json` had no send
failures or missing acknowledged messages, but failed the unchanged 300ms commit p95
gate (766.05ms and 932.28ms). Delivery maxima were 7.32s and 8.24s, below the explicitly
different degraded-mode recovery limit of 20s. These are correctness passes and overall
benchmark failures. The second run overlapped backend tests on the same development
host. `recovery-utilization.json` records sampled process RSS and DB connection counts;
it is neither a peak-memory estimate nor isolated production sizing evidence.

Presence enumeration was changed from a global Redis scan to an expiring per-conversation
index. Multi-tab expiry and an unauthorized visitor subscription have real Redis/socket
regressions. The short outage results do not establish that this change fixes all latency
under degradation.

## Final-run resource sample

`benchmark-utilization.json` contains 120 five-second samples over 600 seconds,
recorded with `apps/backend/.venv/bin/python scripts/sample-benchmark.py --seconds 620`.
Maximum sampled API/dispatcher RSS sum was 425.27 MiB (includes shared pages, excludes
PostgreSQL/Redis/k6/demo processes). Maximum sampled benchmark database connections
were 32, excluding the collector's own connection. Host availability was four CPUs and
7,358,476 KiB physical RAM. No concurrent test/build job was deliberately run during this
final measurement; the host remained a shared development environment.

The full run completed before the later user-initiated container stop. The subsequent
restart is recorded separately and does not change the completed benchmark result.

## Full recovery scenario after restart

The final `bash scripts/run-recovery-benchmark.sh` run used the full 600-second workload
with 200 clients/two APIs, a five-second Redis outage, the burst and 400 socket sessions
including controlled reconnects. No test/build job ran concurrently. Results in
`benchmark-recovery.json` and `benchmark-recovery-console.txt`:

| Signal | Measured |
| --- | --- |
| HTTP message commands | 3,195 |
| Commit p95 | 110.76 ms |
| Delivery p95 | 488 ms |
| Maximum delivery time | 7.87 s |
| Send failures | 0 |
| Client checks | 3,795 passed, 0 failed |
| Per-client acknowledged-message recovery | All 200 clients passed |

All configured thresholds passed: commit p95 below 300ms, zero send failures and
degraded delivery maximum below 20 seconds. Observed delivery p95 also remained below
one second. The recovery script now defaults to 600 seconds; use
`RECOVERY_DURATION_SECONDS=90` only for an explicitly short diagnostic. The script
also fails if any connection/send/acknowledged-delivery check fails. Resource samples
are in `recovery-utilization-final.json`. These measurements do not erase the earlier
short-run failures or establish an isolated causal effect for the presence-index change.
