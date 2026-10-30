# Tarvio / SupportDesk

Persian-first support desk implemented from [the original design](supportdesk-system-design-v1.md).
The design is retained unchanged. See [implementation plan](docs/implementation-plan.md),
[verified progress and remaining work](docs/progress.md), and [bootstrap ADR](docs/adrs/0011-bootstrap-compatibility.md).

The connected Persian RTL interface uses the Tarvio design: operator inbox, customer chat,
knowledge management, entry and login. See the [frontend integration note](docs/frontend-integration.md)
for archive provenance, contract mappings, current checks and responsive screenshots.
Internal service/package names remain SupportDesk.

The portfolio revision adds authorized server-side inbox search, persisted message
titles/previews, one Knowledge activation control, truthful public capabilities and
installation-wide resource limits. The complete Compose package was checked locally;
a small authorized [live Token Factory evaluation](docs/live-provider-verification.md)
now passes. Freestyle deployment and public-provider activation remain unverified. See the
[portfolio handoff](docs/portfolio-release.md) for official provider terms, production
startup, trusted proxies, backup/restore, rollback and missing host inputs.

```mermaid
flowchart LR
    Browser[Persian React UI] -->|REST and WebSocket| API[FastAPI]
    API --> DB[(PostgreSQL and pgvector)]
    Dispatcher[Outbox dispatcher] --> DB
    Dispatcher --> Redis[(Redis)]
    Redis --> API
    Redis --> Worker[Celery worker]
    Worker --> DB
    Worker --> E5[Pinned local E5]
    Worker --> Provider[Explicit fake or configured live provider]
    API --> Files[Private artifacts]
    Worker --> Files
```

## Local development

Requirements: Docker Compose, Python 3.13, uv 0.12.1, Node 24, pnpm 11.20.0.

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d postgres redis
cp .env.example .env
cd apps/backend
uv sync --locked --all-extras
uv run --locked alembic upgrade head
uv run --locked --all-extras python -m supportdesk.cli.seed_demo
uv run --locked --all-extras python -m supportdesk.cli.provision_embeddings
uv run --locked --all-extras python -m supportdesk.cli.seed_knowledge
uv run --locked --all-extras uvicorn supportdesk.main:create_app --factory --reload --host 127.0.0.1 --no-proxy-headers
```

In a second terminal at the repository root:

```bash
pnpm install --frozen-lockfile
pnpm --filter @supportdesk/web dev
```

Open http://localhost:5173 (use this exact origin). `/demo` creates an isolated expiring
workspace with independent customer and staff sessions. `/login` accepts the explicitly
fictional development account `admin@tarvio.invalid`, password `Fictional-Demo-Only-2026!`.
Set `DEMO_PASSWORD` when seeding to use a different local password. The default
`.env.example` selects the explicit simulated provider; live mode requires backend configuration.
The home page's **customer entry** opens `/chat/tarvio-demo`, whose conversations reach
the fixed staff account above. Use a private window for the customer and the normal
window for staff when testing two separate people. **Start an isolated demo** creates
its own workspace and paired staff/customer sessions instead. The shared fixture entry
is shown only when the local backend confirms it exists; production hides that entry.
Run the dispatcher and worker in separate terminals in `apps/backend`:

```bash
uv run --locked --all-extras python -m supportdesk.workers.dispatcher
uv run --locked --all-extras celery -A supportdesk.workers.celery_app:app worker -Q ai,ingestion --concurrency=1
```

Wait for all five fictional documents to be ready, then start a fresh demo. It clones
only verified fictional fixture content into the new workspace. Customer messages,
operator claims/replies, assistant citations, handoff, refresh and reconnect use the real
PostgreSQL/Redis/Celery backend. Fake answers are deterministic source excerpts.

After the one-time setup, `bash scripts/start-local.sh` starts PostgreSQL/Redis and
restarts the project's supervised API, dispatcher, worker and frontend together.
Use it again after stopping the containers. It preserves the existing database/files,
checks that an old supervisor PID belongs to this project, and waits for readiness.

A 60–90 second walkthrough: start a demo, ask about the trial, open source S1, request a
human, switch to the operator, claim and reply, refresh the customer, then inspect the
knowledge page. [UI evidence](docs/evidence/portfolio/customer-1440.png), [evaluation](docs/evaluation.md)
and [operations](docs/runbook.md) describe exactly what was checked. The [earlier release manifest](docs/evidence/release.json) records the pre-Tarvio source revision, lockfile hashes, images and verification boundaries; current frontend evidence is linked from the integration note.

## Verification

Tests require a dedicated database ending in `_test`; the fixture refuses other names.

```bash
docker compose exec -T postgres psql -U supportdesk -c 'CREATE DATABASE supportdesk_test;'
cd apps/backend
DATABASE_URL=postgresql+psycopg://supportdesk:local-development-only@127.0.0.1:55432/supportdesk_test uv run --locked alembic upgrade head
uv run --locked --all-extras pytest -q
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy src
uv run --locked alembic check
cd ../..
pnpm contracts:check
pnpm lint
pnpm typecheck
pnpm --filter @supportdesk/web test
pnpm build
LLM_PROVIDER=fake FAKE_SCENARIO=slow bash scripts/start-local.sh
pnpm --filter @supportdesk/web test:e2e
bash scripts/start-local.sh
```

Test database creation is a one-time command. Dependencies and fixtures remain on the
local machine. `docker compose -f compose.yaml -f compose.dev.yaml stop` stops services
without deleting their data. Production deployment is not yet verified; do not expose
the development database owner or fixture credentials publicly.

Pytest forces the simulated provider and configuration unit tests ignore private LLM
settings. The browser suite also needs the explicit fake startup above; the final
restart restores the provider selected by `.env`. Live evaluation uses only the opt-in
CLI described in the live verification note, rather than the broad deterministic suite.


The implementation is a local working demo. Required release gates still under verification
are tracked in `docs/progress.md`; the presence of deployment files does not imply a completed
production release. Live checks cover the recorded local cases; independent human
faithfulness ratings, public-provider permission and deployment-host checks remain open.


Recorded demo: [customer flow video](docs/evidence/demo.webm). The direct customer page is
`/chat/<public_key>`; staff routes use `/app/<workspace_id>/inbox` and `/knowledge`.
Automated browser checks use an existing Chrome executable (`CHROME_PATH` may override it).
Install the project-local recording encoder from the root with
`PLAYWRIGHT_BROWSERS_PATH="$PWD/.local/playwright" pnpm --filter @supportdesk/web exec playwright install ffmpeg`,
then run `pnpm --filter @supportdesk/web test:e2e`.
