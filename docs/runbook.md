# Runbook

## Development

From the root start `docker compose -f compose.yaml -f compose.dev.yaml up -d postgres redis`.
In `apps/backend`: `uv sync --locked --all-extras`, `uv run --locked --all-extras alembic upgrade head`,
`uv run --locked --all-extras python -m supportdesk.cli.seed_demo`,
`uv run --locked --all-extras python -m supportdesk.cli.provision_embeddings`, then
`uv run --locked --all-extras python -m supportdesk.cli.seed_knowledge`.

Start API: `uv run --locked --all-extras uvicorn supportdesk.main:create_app --factory --host 127.0.0.1 --no-proxy-headers`.
Start dispatcher: `uv run --locked --all-extras python -m supportdesk.workers.dispatcher`.
Start worker: `uv run --locked --all-extras celery -A supportdesk.workers.celery_app:app worker -Q ai,ingestion --concurrency=1`.
From root: `pnpm install --frozen-lockfile`; `pnpm --filter @supportdesk/web dev`.
Use `http://localhost:5173`; wait for five documents to become ready before opening a new demo.
After initial setup, `bash scripts/start-local.sh` from the root restarts the local
containers and supervised application roles and verifies the seeded demo is ready.
It may replace the previous local supervisor only after validating its command,
working directory and process group. Logs/PID remain in ignored `.local/`.
The model provision command may need unsupported host SOCKS proxy environment variables
removed while retaining the configured HTTP proxy; runtime inference never downloads weights.

## Failure recovery

Database outage: sends must fail without acknowledgement. Keep the original client ID
and retry after recovery. Redis outage: REST chat remains available; socket watermark
checks repair committed events. Restart Redis and dispatcher to reconstruct due jobs.
A worker crash leaves a lease; recovery issues a new token after expiry. At most three
attempts may execute; old tokens cannot finalize. Investigate a terminal job before
an administrator uses the audited manual retry endpoint.

Inspect `/api/v1/health/live` and `/api/v1/health/ready`. Readiness requires the expected
schema. Check pending outbox age, failed/expired jobs, disk usage and source status.
Do not log bodies, prompts, tokens or API keys when investigating failures.

`/metrics` is an internal scrape endpoint and is not proxied by the public Caddy route.
Scrape each API every 30 seconds: HTTP/socket/event counters belong to that process;
outbox, job, run and usage gauges are shared database snapshots and must not be summed
across API replicas. Labels contain bounded kinds/states, never tenant/actor identifiers.
Database metrics use a read-only transaction with a two-second statement timeout and
report `supportdesk_metrics_database_available=0` if collection fails. Alert initially
on outbox age above 30 seconds, expired leases, unknown-usage growth and sustained
HTTP errors. Event delivery histograms include replay backlog age. AI first-token timing
is emitted as a structured `ai.first_token` job log; recent queue/total means use retained
database timestamps and are not provider percentile measurements.

## Production preparation

Use `deploy/compose.production.yaml` and a private file based on
`deploy/production.env.example`. The exact startup procedure is:

```bash
PORTFOLIO_ENV_FILE=.env.production bash scripts/production-start.sh
```

It builds all three images, waits for private dependencies, applies schema 0008,
creates the restricted runtime role, provisions pinned E5, seeds fictional templates,
starts API/dispatcher/worker/retention and waits for current fixture hashes before
the gateway. Runtime containers do not receive the owner URL. Use exact HTTPS origins,
secure cookies, immutable `RELEASE_ID` tags and persistent DB/files/models/Redis volumes.
Leave `DEMO_MODE=false` for private installations, or explicitly enable isolated,
expiring public demos. Production template seeding creates no reusable staff account;
create a private administrator with `supportdesk.cli.create_staff` when needed.

The gateway binds loopback by default. Freestyle ingress needs `GATEWAY_BIND_ADDRESS=0.0.0.0`,
an authorized TLS rule/firewall and actual edge CIDRs. Uvicorn forwarding is disabled;
the application trusts only the fixed gateway and Caddy validates the edge chain before
replacing forwarding headers. See [the complete Freestyle handoff](portfolio-release.md)
for lifecycle limits, proxy settings, source transfer and missing deployment inputs.
Never trust all proxy addresses or expose PostgreSQL/Redis ports.

Shared daily AI reservations, concurrency/queue, demo/upload/storage and ingestion
limits are documented in that handoff. Public live generation is separately gated by
`PUBLIC_LIVE_AI_ENABLED`; provider terms must permit the intended audience. A live
failure never selects the simulated adapter. Model context does not enlarge the
application input/output reservation. Inspect unknown-usage charges when troubleshooting.

The supervised `retention` role runs expiry/retention hourly with a 300-second subprocess
bound and database exclusion lock. Verify its logs after rollout. `purge` remains a
one-shot maintenance command. The old systemd templates are alternatives; do not enable
both schedules. Compose logs rotate at five 10 MiB files per service; a 14-day policy
requires a host collector. No host timer or external collector was installed locally.
Keep off-host backup scheduling separate and configure its encrypted destination.

## Backup and restore

Daily encrypted off-host backups remain deployment operations. Drain writes/purges for
a coordinated artifact backup. Dump PostgreSQL using `pg_dump -Fc`, copy immutable files,
and save a SHA-256 manifest. Encrypt and transfer to the configured backup destination.
Restore into a new database with `pg_restore`, restore files into a separate private
folder and verify every referenced artifact hash before switching traffic. Never test
a restore by overwriting the live database. RPO 24 hours / RTO 2 hours are targets until
an off-host encrypted restore has been timed on the deployment host.

For the complete Compose package, `scripts/production-backup.sh` coordinates stopped
writers, PostgreSQL dump, private artifacts and a hash manifest, encrypts with the
configured age recipient and restarts writers through a trap. The companion
`scripts/production-restore-drill.sh` restores to a new `*_test` database and directory.
The portfolio local drill verified 87 artifact hashes; it explicitly used unencrypted
local storage and does not satisfy encrypted off-host recovery. Exact commands,
rollback/schema compatibility and host gates are in the [portfolio handoff](portfolio-release.md#backup-restore-and-rollback).

For the fictional local development setup, `bash scripts/restore-drill.sh` creates a new
timestamped `*_test` database and a private `.local/restore-*` copy, restores the dump and
verifies every referenced ready artifact's size and SHA-256. Pause purge jobs while taking
the snapshot. It preserves existing databases and writes the measured result to
`docs/evidence/restore.json`. Remove the drill database/private backup later using the
exact name in that report; the script never deletes an existing database.
