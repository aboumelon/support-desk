# SupportDesk

Persian-first support desk implemented from [the original design](supportdesk-system-design-v1.md).
The design is retained unchanged. See [implementation plan](docs/implementation-plan.md),
[verified progress and remaining work](docs/progress.md), and [bootstrap ADR](docs/adrs/0011-bootstrap-compatibility.md).

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
uv run alembic upgrade head
uv run --all-extras python -m supportdesk.cli.seed_demo
uv run --all-extras python -m supportdesk.cli.provision_embeddings
uv run --all-extras python -m supportdesk.cli.seed_knowledge
uv run --all-extras uvicorn supportdesk.main:create_app --factory --reload --host 127.0.0.1
```

In a second terminal at the repository root:

```bash
pnpm install --frozen-lockfile
pnpm --filter @supportdesk/web dev
```

Open http://localhost:5173 (use this exact origin). `/demo` creates an isolated expiring
workspace with independent customer and staff sessions. `/login` accepts the explicitly
fictional development account `admin@naran.invalid`, password `Fictional-Demo-Only-2026!`.
Set `DEMO_PASSWORD` when seeding to use a different local password. No live AI call is made.
Run the dispatcher and worker in separate terminals in `apps/backend`:

```bash
uv run --all-extras python -m supportdesk.workers.dispatcher
uv run --all-extras celery -A supportdesk.workers.celery_app:app worker -Q ai,ingestion --concurrency=1
```

Wait for all five fictional documents to be ready, then start a fresh demo. It clones
only verified fictional fixture content into the new workspace. Customer messages,
operator claims/replies, assistant citations, handoff, refresh and reconnect use the real
PostgreSQL/Redis/Celery backend. Fake answers are deterministic source excerpts.

A 60–90 second walkthrough: start a demo, ask about the trial, open source S1, request a
human, switch to the operator, claim and reply, refresh the customer, then inspect the
knowledge page. [UI evidence](docs/evidence/customer-chat.png), [evaluation](docs/evaluation.md)
and [operations](docs/runbook.md) describe exactly what was checked.

## Verification

Tests require a dedicated database ending in `_test`; the fixture refuses other names.

```bash
docker compose exec -T postgres psql -U supportdesk -c 'CREATE DATABASE supportdesk_test;'
cd apps/backend
DATABASE_URL=postgresql+psycopg://supportdesk:local-development-only@127.0.0.1:55432/supportdesk_test uv run alembic upgrade head
uv run --all-extras pytest -q
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run alembic check
cd ../..
pnpm contracts:check
pnpm lint
pnpm typecheck
pnpm build
```

Test database creation is a one-time command. Dependencies and fixtures remain on the
local machine. `docker compose -f compose.yaml -f compose.dev.yaml stop` stops services
without deleting their data. Production deployment is not yet verified; do not expose
the development database owner or fixture credentials publicly.


The implementation is a local working demo. Required release gates still under verification
are tracked in `docs/progress.md`; the presence of deployment files does not imply a completed
production release. Live-provider checks and independent human faithfulness ratings are unverified.


Recorded demo: [customer flow video](docs/evidence/demo.webm). The direct customer page is
`/chat/<public_key>`; staff routes use `/app/<workspace_id>/inbox` and `/knowledge`.
Automated browser checks use an existing Chrome executable (`CHROME_PATH` may override it).
Install the project-local recording encoder from the root with
`PLAYWRIGHT_BROWSERS_PATH="$PWD/.local/playwright" pnpm --filter @supportdesk/web exec playwright install ffmpeg`,
then run `pnpm --filter @supportdesk/web test:e2e`.
