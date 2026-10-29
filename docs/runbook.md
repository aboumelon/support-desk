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

## Production preparation

Use `deploy/compose.production.yaml`, a strong ignored `.env.production`, a restricted
runtime role and a separate migration-owner URL. Set exact HTTPS origins, secure cookies,
private storage/model volumes and `DEMO_MODE=false`. Run migrations once before API rollout.
Provision the pinned model explicitly in the worker image/volume. Create the initial
administrator using `python -m supportdesk.cli.create_staff --email ... --workspace-key ... --name ...`.
Place a TLS terminator before the loopback gateway. Production container and restore
verification outcomes are recorded in `progress.md`; do not infer successful deployment
from the presence of a Compose file.

## Backup and restore

Daily encrypted off-host backups remain deployment operations. Drain writes/purges for
a coordinated artifact backup. Dump PostgreSQL using `pg_dump -Fc`, copy immutable files,
and save a SHA-256 manifest. Encrypt and transfer to the configured backup destination.
Restore into a new database with `pg_restore`, restore files into a separate private
folder and verify every referenced artifact hash before switching traffic. Never test
a restore by overwriting the live database. RPO 24 hours / RTO 2 hours are targets until
an off-host encrypted restore has been timed on the deployment host.
