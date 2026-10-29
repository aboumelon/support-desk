# Local two-API benchmark, 2026-10-29

Environment: Linux development host, 4 available CPUs, approximately 7 GiB physical RAM;
PostgreSQL 17/pgvector 0.8.0, Redis 8.0.2, Python 3.13.14, two Uvicorn API processes,
separate dispatcher, no LLM work in the benchmark workspace. Other local development
processes were present; this is not a dedicated production-capacity measurement.

Command: `bash scripts/run-benchmark.sh`, after starting the isolated benchmark services.
k6 image: `grafana/k6:1.0.0` (digest `sha256:f21270290d702cbf0a7d6ba5d7ed100b63bcb233b558b885ed787547b3488279`).
The fixture command refuses any database not ending in `_benchmark`. Credentials remain
in ignored `.local/benchmark-sessions.json`; no credential is included in this report.

The corrected full ten-minute run used 200 clients split across two API instances,
a short 20-message/second burst and a staggered reconnect wave. Results:

| Signal | Measured |
| --- | --- |
| HTTP message commands | 3,194 |
| Observed HTTP command rate including burst | 5.31/s |
| Message commit p95 | 92.36 ms |
| Message delivery p95 | 430.05 ms |
| Message command failures | 0 |
| WebSocket sessions including reconnects | 400 |
| k6 checks | 3,594 passed, 0 failed |

Both configured p95 thresholds and the zero-failure gate passed. Delivery is measured
from a client timestamp inserted before the REST send, so it includes commit latency.
Maximum observed commit/delivery times were about 5.2/5.4 seconds; passing p95 does not
imply every request met the target. The original failed run and short intermediate run
are retained as JSON next to `benchmark-final.json`.

Failure diagnosis and correction: workspace-wide notifications caused unrelated replay
queries, a one-row/250ms loop could dispatch fewer events than the requested send rate,
and message quota checking acquired another DB connection while holding the first.
The implementation now filters notification subscriptions, drains outbox batches and
checks quotas within the message transaction. Final dispatcher polling is 250 ms.

Separate reliability tests exercise two actual API processes, a lost last notification,
real Redis outage/restart and an actual Celery SIGKILL followed by lease expiry and
queue reconstruction. Recovery/load behavior beyond the tested scenario is not a
high-availability or production capacity guarantee.
