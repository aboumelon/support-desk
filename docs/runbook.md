# Runbook

## Development

From the root start `docker compose -f compose.yaml -f compose.dev.yaml up -d postgres redis`.
In `apps/backend`: `uv sync --locked --all-extras`, `uv run --all-extras alembic upgrade head`,
`uv run --all-extras python -m supportdesk.cli.seed_demo`,
`uv run --all-extras python -m supportdesk.cli.provision_embeddings`, then
`uv run --all-extras python -m supportdesk.cli.seed_knowledge`.

Start API: `uv run --all-extras uvicorn supportdesk.main:create_app --factory --host 127.0.0.1`.
Start dispatcher: `uv run --all-extras python -m supportdesk.workers.dispatcher`.
Start worker: `uv run --all-extras celery -A supportdesk.workers.celery_app:app worker -Q ai,ingestion --concurrency=1`.
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

Use `deploy/compose.production.yaml`, a strong ignored `.env.production`, a restricted
runtime role and a separate migration-owner URL. Set exact HTTPS origins, secure cookies,
private storage/model volumes and `DEMO_MODE=false`. Run migrations once before API rollout.
Provision the pinned model explicitly in the worker image/volume. Create the initial
administrator using `python -m supportdesk.cli.create_staff --email ... --workspace-key ... --name ...`.
Place a TLS terminator before the loopback gateway. Production container and restore
verification outcomes are recorded in `progress.md`; do not infer successful deployment
from the presence of a Compose file.

Daily retention is a one-shot `purge` maintenance service. The example units under
`deploy/systemd/` assume `/opt/supportdesk`; change that path for the installation,
then install/enable `supportdesk-retention.timer` on the deployment host. They are
templates and have not been installed on this development machine. Verify the first
run and monitor the timer before relying on retention. Keep operational logs for
14 days using the deployment host's log collector policy. Off-host backup scheduling
requires the actual encrypted destination and credentials.

## Backup and restore

Daily encrypted off-host backups remain deployment operations. Drain writes/purges for
a coordinated artifact backup. Dump PostgreSQL using `pg_dump -Fc`, copy immutable files,
and save a SHA-256 manifest. Encrypt and transfer to the configured backup destination.
Restore into a new database with `pg_restore`, restore files into a separate private
folder and verify every referenced artifact hash before switching traffic. Never test
a restore by overwriting the live database. RPO 24 hours / RTO 2 hours are targets until
an off-host encrypted restore has been timed on the deployment host.

For the fictional local development setup, `bash scripts/restore-drill.sh` creates a new
timestamped `*_test` database and a private `.local/restore-*` copy, restores the dump and
verifies every referenced ready artifact's size and SHA-256. Pause purge jobs while taking
the snapshot. It preserves existing databases and writes the measured result to
`docs/evidence/restore.json`. Remove the drill database/private backup later using the
exact name in that report; the script never deletes an existing database.
