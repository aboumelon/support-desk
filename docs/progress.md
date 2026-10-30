# SupportDesk implementation progress

Last updated: 2026-10-30 (Asia/Tehran). Authority: [original design](../supportdesk-system-design-v1.md).

## Portfolio release preparation (2026-10-30)

- [x] Authorized server-side search/cursors, persisted titles/previews, focused navigation and accurate public capabilities/demo copy.
- [x] Compatible single-system prompts, strict streamed-provider parsing, bounded timeout/retry/usage accounting and opt-in live evaluation.
- [x] Shared atomic AI budget/admission, global ingestion/storage/demo limits, trusted proxy handling and scheduled expiry cleanup.
- [x] Complete-stack Freestyle package, restricted roles, health/startup/recovery, backup and rollback instructions.
- [x] Final image revision/startup check and machine-readable handoff evidence.

Implemented behavior and host instructions: [portfolio handoff](portfolio-release.md).
Current UI mappings/screenshots: [frontend integration](frontend-integration.md).
The original design, existing lockfiles and unrelated untracked `skills/` were preserved.
Historical release, Tarvio and benchmark reports/images below remain tied to their own
source revisions and were not overwritten or used as current performance proof.

Fresh local results:

- Backend: **73 passed in 153.68s**, using isolated PostgreSQL `supportdesk_test` and Redis 15. Includes authorized search/cursors, cross-workspace budgets/admission, unknown-usage retention after expiry, trusted forwarding, uploads, prompt/SSE/deadline/rate-limit cases and actual Redis/Celery crash/lease recovery. Ruff format (92 files), Ruff lint, strict mypy (64 source files), `alembic check` and migration 0008 upgrades passed.
- Frontend: formatting, ESLint, TypeScript, **7 unit cases**, generated-contract drift and production build passed. Main entry remains about 415 KiB before gzip; this is build output, not a performance target.
- Browser: **8 passed in 1.9m** with real API/PostgreSQL/Redis/dispatcher/Celery/E5 and explicit fake generation. Covers first-page-independent search (56 conversations), Settings redirect, capability-disabled/retry states, separate audience logout, expired staff route, messaging/idempotent retry/offline/refresh/reconnect, citations/source failure, handoff during generation, real ingestion/withdrawal/permissions, 105 control events and responsive accessibility. Final responsive-only rerun: **1 passed in 25.0s** after text-direction/placeholder adjustments.
- Current screenshots are separately stored in `evidence/portfolio/`: customer/operator/knowledge at 1440/1024/768/390, source sheets at 1024/768/390 and entry/login at 1440/390. Rendered desktop, tablet and mobile screens were inspected. Reduced-height focused composer was checked in browser emulation; no physical mobile keyboard claim.
- Fresh 40-case Tarvio fixture report: recall@5 **1.0**, handoff **0.975**, no source-isolation failures, valid labels. `evidence/rag-portfolio.json` records actual E5 retrieval and deterministic answers; no live/human faithfulness claim.
- Isolated production-shaped project `supportdesk-portfolio-check`: private PostgreSQL/Redis and named DB/files/model volumes, loopback gateway 5182, restricted runtime role, pinned offline model provisioning and five ready fixture hashes passed. Actual HTTP messaging/retry/citation/handoff/claim/reply/resolve/reopen/upload/withdrawal and **10 ordered WebSocket replay events through Caddy** passed. Only gateway publishes a port; owner credentials are absent from runtime roles and runtime schema creation was denied.
- Trusted synthetic edge addresses get independent session buckets; six attempts with spoofed forwarding from an untrusted API container still hit the same five/minute bucket (**200 × 5, then 429**). Actual Freestyle edge identity remains a host gate.
- Full role/database/Redis restart preserved all **3 canonical smoke messages** in named volumes. Coordinated backup/restore to a new `*_test` database and private directory verified **87 artifact hashes**. This was explicitly unencrypted and local; encrypted off-host restore remains unverified.

Commands run from root (private environment/session files remain ignored):

```bash
pnpm exec prettier --check apps/web/src apps/web/e2e apps/web/index.html apps/web/package.json
pnpm lint
pnpm typecheck
pnpm --filter @supportdesk/web test
pnpm contracts:generate
pnpm contracts:check
pnpm build
FAKE_SCENARIO=slow bash scripts/start-local.sh
pnpm --filter @supportdesk/web test:e2e
pnpm --filter @supportdesk/web test:e2e --grep 'desktop/tablet/mobile'
bash scripts/start-local.sh
docker compose --env-file .local/portfolio.production.env -f deploy/compose.production.yaml config --quiet
docker compose --env-file .local/portfolio.production.env -f deploy/compose.production.yaml build api worker gateway
PORTFOLIO_ENV_FILE=.local/portfolio.production.env bash scripts/production-start.sh
docker compose --env-file .local/portfolio.production.env -f deploy/compose.production.yaml exec -T gateway caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked --project apps/backend --all-extras python scripts/verify-production-stack.py
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked --project apps/backend --all-extras python scripts/verify-production-stack.py --resume
PORTFOLIO_ENV_FILE=.local/portfolio.production.env ALLOW_UNENCRYPTED_LOCAL_BACKUP=1 bash scripts/production-backup.sh
PORTFOLIO_ENV_FILE=.local/portfolio.production.env bash scripts/production-restore-drill.sh "$PRIVATE_BACKUP_DIRECTORY"
```

Backend commands from `apps/backend`:

```bash
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked alembic upgrade head
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked alembic check
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked ruff format --check .
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked ruff check .
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked mypy src
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked --all-extras pytest -q
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked --all-extras python -m supportdesk.cli.evaluate_rag
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked --all-extras python -m supportdesk.cli.evaluate_live --allow-live
```

The last command deliberately refused absent backend live configuration before any
external inference. No successful live request, authenticated provider model listing,
Freestyle account/VM operation, public endpoint, remote push or paid service occurred.
Only secret presence was inspected; values are excluded from code, logs and evidence.
Official AMD/Freestyle references and current public-use constraints are linked in the
handoff. Public live admission defaults off; no fallback changes a live error to fake.

Corrected intermediate failures: initial SSE mocks and formatting/types; a global
concurrency test needed to advance its intentionally deferred five-second job; browser
fixtures needed an explicit allowed Origin and message-scoped selectors after real
titles/previews. A subsequent final usage-buffer change required an explicit narrowed
integer type; the complete 73-case suite above passed afterward. An offline cache copy
initially omitted shared symlink blobs; dereferencing them fixed pinned provisioning.
The isolated Docker network initially collided with the fixed gateway and then chose
the test edge address as bridge; explicit dynamic range and bridge settings corrected
both, followed by actual bucket/restart verification. No development data was truncated.

Final source checkpoint: `aadc8f3661145e50613959bf5901c6fd5ba6494f` on local
`codex/tarvio-frontend`. The complete `production-start.sh` procedure passed against
that source, including all three revision-labeled images, roles, model provisioning,
fixture readiness and gateway. The fresh container smoke and persisted-message resume
passed again. Caddy validation passed inside the running gateway; an auxiliary
`compose run gateway` validation attempt conflicted with the active gateway's fixed
IP, so the correct `compose exec -T gateway caddy validate ...` check was used.
Image IDs, file/lock/design hashes, screenshots and boundaries are recorded in
[the current manifest](evidence/portfolio.json). Final documentation/evidence follow
in a separate local commit; application source and images use the checkpoint above.
Ordinary fake generation was restored with `bash scripts/start-local.sh`; API readiness
is schema 0008 / Redis ok and frontend 5173 is available. No new load benchmark was run.
The isolated verification containers/network were stopped afterward with
`docker compose --env-file .local/portfolio.production.env -f deploy/compose.production.yaml down --remove-orphans`;
all four named volumes, private backup and restored test data were preserved. The main
development PostgreSQL/Redis/application remain running. Source-only ZIP/tar exports
are created from the final local Git revision under ignored `.local/exports/`; dependencies,
credentials, sessions, model weights, databases, local artifacts and unrelated `skills/`
are excluded. Both lockfiles and `.env.example` templates remain in the source package.

Remaining public-release inputs/gates: authorized Freestyle VM/account/domain and actual
edge CIDRs/firewall; private production secrets; provider key/base/model/context and
permitted public-use decision (or another compatible provider); encrypted backup
recipient/destination and host restore; real HTTPS/WebSocket/cookie/two-visitor checks;
physical keyboard check and independent human/blind quality evaluation. No historical
load measurement is transferred to this revision or a new host.

## Historical implementation record (through 2026-10-29)

The sections below describe earlier checkpoints; the current status and commands above
take precedence where behavior, schema, scheduling or verification counts changed.

## Completed and verified

- Root established directly at `/home/armin/projects/support-desk`; original design and unrelated `skills/` preserved.
- M0: locked Python 3.13 / Node 24 monorepo; validated config; Alembic; fictional seed; separate opaque staff/customer sessions; CSRF/origin/rate limits; isolated expiring demo workspaces; tenant tests; CI definition.
- M1: atomic message/event/outbox writes; actor/client-ID retry/conflict behavior; command receipts; consistent snapshots; pagination; monotonic read cursors. PostgreSQL concurrency tests and browser refresh persistence pass.
- M2 core gates: competing claims; real two-API delivery; lost final notification repaired without a later event; reconnect replay; bounded sender; inbox/ownership UI. Real Redis/Celery ingestion and duplicate dispatch also verified.
- M3 core: private bounded uploads, immutable versions, ready-only pgvector retrieval, replacement-pending and withdrawal behavior. Pinned E5 revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`; actual CPU inference produces 384 dimensions.
- M4 core: explicit fixture/live adapters, provisional drafts, citations, conservative usage reservations and bounded retries. Fake-provider tests cover handoff, superseding turns, withdrawal, source replacement, stale leases, invalid citations, budgets and unknown timeout/429/drop usage.
- Final serialized backend suite: **41 passed in 140.06s**, including the real prefixed Redis/Celery crash/queue recovery, operational metrics, configuration, 200-event replay, multi-tab presence and unauthorized presence checks. The separate prefixed-broker regression also passed (2 cases, 98.71s).
- Frontend: ESLint, strict TypeScript, four realtime/Markdown safety unit tests, generated contract drift check and production Vite build passed. Route splitting reduces the main bundle below 500 KiB.
- Playwright: isolated customer/operator contexts completed assistant answer/citation, handoff, claim/reply and refresh persistence; **2 passed in 32.1s**, including direct staff login, offline message recovery, resolve/reopen and public customer chat preserving the actor after refresh. Customer/operator/knowledge screenshots are in `docs/evidence/`.
- API, gateway and CPU worker container builds passed. Non-root worker app startup/E5 inference and Caddy validation passed. Production Compose configuration validation passed without deployment.
- Restore drill: PostgreSQL restored to a fresh `supportdesk_drill_*_test` in 2.06 seconds using `bash scripts/restore-drill.sh`; all **40 referenced artifact hashes** matched a separate file copy. Off-host encrypted restore remains unverified.
- Forty-case fixture evaluation: recall@5 **1.0**, fixture handoff **0.975**, zero source-isolation failures, valid source IDs. Original threshold-only handoff was **0.625**; both reports are retained. Human faithfulness ratings and a fresh blind evaluation are uncollected.

## Deployment and verification boundaries

- Assigned/unread inbox filters, expiry cleanup, source/config changes, health degradation and bounded operational metrics passed the final backend regression. Database-backed outbox/job/AI gauges and process-local realtime counters are implemented; first-token timing is logged.
- Light API/dispatcher and CPU worker Docker targets, private production Compose, Caddy, runtime-role SQL and runbook. Production Compose has not been deployed.
- The corrected full load run passed: 200 connections, two APIs, 3,192 commands, zero failures, p95 commit 80.26 ms and p95 delivery 416.00 ms. See `evidence/benchmark.md`.

## Honest failures and corrections

- Initial SQLAlchemy asyncio dependency, migration constraint naming and model-discovery errors were corrected and migrations rerun. Migrations 0006/0007 retain upgrade continuity.
- Initial Playwright attempts failed while standalone API/worker processes had stopped. A local supervisor now keeps the demo roles together; the subsequent flow passed.
- First full 200-client benchmark failed: p95 message commit about 50 seconds and p95 delivery about 113 seconds, with 483 send failures. Evidence is retained in `benchmark-before-fixes.json`.
- Fixes: notify only matching subscriptions; drain outbox in batches; evaluate message quotas within the current DB transaction. Short 200-client rerun had **zero send errors**, p95 commit **276 ms**, p95 delivery **1.21 s**. Idle dispatcher polling was then reduced to 250 ms before the full corrected rerun.
- Git metadata was initially empty/inaccessible. Authorized local `git init` succeeded outside the restricted mount. Source checkpoint `f4976cceb2e7698f647f3136f98528f80069965f` includes both lockfiles. Final image IDs and verification provenance are recorded in `evidence/release.json`. No remote push or deployment has occurred.

## Remaining release gates / limitations

- Full healthy-load targets and 200-event replay passed. Actual Redis outage/restart and Celery SIGKILL/lease-expiry/queue-reconstruction tests passed separately. Two short 200-client Redis-outage runs preserved every acknowledged message with no send failures, but failed the 300ms commit p95 target (766ms and 932ms). The latter overlapped backend tests; neither is reported as a passing performance run. Reports are retained. Both final full-duration runs passed: healthy 3,192 sends / zero errors; recovery 3,195 sends / zero errors and all acknowledged messages delivered. Performance targets are not capacity guarantees.
- Source, tree, lockfile, contract, model, prompt, migration and image identities are recorded in `evidence/release.json`. Final load measurement completed against that source checkpoint before the subsequent user-initiated container stop. The console report and 120 resource samples are retained.
- PDF page/OCR/byte/encoding and real E5 chunk-window checks passed. Multi-tab presence expiry and authorization passed real Redis/socket tests. Broader PDF fuzzing and full multi-tab UI receipt coverage remain useful release-hardening checks.
- Retention schedules now cover messages, citations, events, commands, audits, outbox, eligible jobs, withdrawn chunks, demo expiry and orphan files. AI job identity tombstones have an explicit ADR exception. Operational gauges and daily-retention service/timer templates are implemented. Enabling production scheduling, configuring alert/log collection and independent deployment restore timing remain deployment operations.
- Live provider: **unverified**; no credentials or paid API calls used. Human-rated claim support, untouched blind RAG cases and an off-host encrypted backup drill remain needed before a public release claim.
- A local working demo is available; **M0–M5 are not declared fully complete while the above required gates remain**.

## Exact verification commands

Run backend commands from `apps/backend`:

```bash
uv sync --locked --all-extras
uv run --all-extras alembic upgrade head
uv run --all-extras alembic check
uv run --all-extras ruff format --check .
uv run --all-extras ruff check .
uv run --all-extras mypy src
uv run --all-extras pytest -q --tb=short
uv run --all-extras python -m supportdesk.cli.evaluate_rag
```

Tests use isolated `supportdesk_test` and Redis database 15. Never use the demo database
for truncating tests. The benchmark uses `supportdesk_benchmark` and Redis database 14.

Run frontend checks from root:

```bash
pnpm install --frozen-lockfile
pnpm contracts:check
pnpm lint
pnpm typecheck
pnpm --filter @supportdesk/web test
pnpm build
pnpm --filter @supportdesk/web test:e2e
```

The Playwright test uses the actual running API/dispatcher/worker and local Chrome.
Local supervisors and logs live under ignored `.local/`; services run on API 8000,
frontend 5173, PostgreSQL 55432 and Redis 56379.

## Next concrete step

Collect fresh blind cases and independent human claim-support ratings using the
evaluation rubric; configure a real encrypted backup destination and time an off-host
restore before any public release claim. Live-provider verification
requires separate authorized credentials/budget. The local demo remains the supported
fixture-mode outcome, with `bash scripts/start-local.sh` to recover after a container stop.


## Final failure/recovery evidence additions

- Actual Redis service outage/restart: two network reliability tests passed in 38.49s; human REST chat and periodic repair survived.
- Actual Celery SIGKILL, unmodified lease-clock expiry and broker reconstruction plus parser limits: four checks passed in 85.45s.
- One full test invocation overlapped a separate fixture-truncating test invocation, causing test-database interference. A session-wide PostgreSQL advisory lock now serializes pytest invocations; the subsequent full suite passed.
- Safe Markdown disables raw HTML and unsafe URL schemes, with passing renderer tests. Public/staff routes and canonical assistant-setting bootstrap are implemented.
- Demo recording: `evidence/demo.webm` (26.52 seconds, automated real customer flow). Screenshots and the longer manual walkthrough are linked from README.

- Expanded browser checks exposed a resolved transcript disappearing with its filtered inbox row. Selection now persists; offline delivery, resolve/reopen and refresh checks passed afterward.
- A separate browser CI job starts the real API/dispatcher/Celery roles and pinned E5 fixtures. Its constituent local commands passed; the remote GitHub job is unexecuted because no push was requested.

- Presence now uses a per-conversation sorted-set index instead of scanning Redis globally. Conversation authorization occurs before any ephemeral identity is read or queued.

## Resumed after the user stopped containers

- The completed final ten-minute benchmark was preserved; it was not interrupted by the later stop.
- PostgreSQL and Redis were restarted with `docker compose -f compose.yaml -f compose.dev.yaml up -d --wait postgres redis`; both are healthy and API readiness reports schema 0007 / Redis ok.
- Added `bash scripts/start-local.sh` to restart the project-owned application supervisor safely and wait for the seeded app. Browser recovery verification passed: **2 passed in 26.2s** after the container restart. Customer/operator assistant/human flows, offline replay, resolve/reopen and refresh persisted.

- The full ten-minute, 200-client/two-API Redis-outage run passed in isolation from tests/builds: 3,195 sends, zero send failures, all 200 acknowledged-message checks passed, commit p95 110.76ms and delivery p95 488ms (maximum 7.87s). The two earlier short failed measurements are retained. `RECOVERY_DURATION_SECONDS` can explicitly select a shorter diagnostic run; the default now matches the ten-minute scenario.

- Final recovery report: `evidence/benchmark-recovery.json`; terminal report: `evidence/benchmark-recovery-console.txt`. The restart helper stale-PID guard was exercised against an unrelated-command test process; it refused to signal it and preserved the running app.

## Tarvio frontend integration (2026-10-29)

The latest prototype is connected to the existing application. Entry/login, operator
inbox, customer chat, responsibility/timeline, source inspector, knowledge and settings
use real authorized APIs. The archive/config separation, typed mappings, component
structure, exact verification commands and screenshots are in [the integration note](frontend-integration.md).

- Final browser sweep: **5 passed in 1.4m**, covering real customer/staff flows, offline recovery, retry after server commit with one canonical message, handoff while streaming, independent drafts, admin ingestion/failed replacement/withdrawal, activation, authorization boundaries, and 105 persisted transition events across pages.
- Responsive customer/operator/knowledge screenshots inspected at 1440/1024/768/390; source modal keyboard/focus/inert/Escape/restoration and a 390x520 focused composer passed. Entry/login screenshots were also inspected at 1440/390.
- Full backend suite: **42 passed in 136.93s** on PostgreSQL, including worker-crash/lease recovery. Ruff formatting/lint and configured strict mypy (54 files) passed. The retained-event recovery regression is included; no migration was required.
- Frontend lint, types, formatting, production build, 7 unit tests and contract drift passed. Fonts/assets are local with OFL licenses. Vite remains 7.3.7.
- Corrected intermediate failures: source accessible label, citation 410 rendering, reverse-tab modal focus containment, asynchronous activation checkbox and HTML formatting. The auxiliary mobile screenshot selector was corrected. A root-directory mypy attempt missed backend settings and was stopped; the correct backend-directory invocation passed. Two upstream Zod annotation warnings remain nonfatal build output.
- Restored ordinary local provider settings after the slow-generation test. PostgreSQL/Redis are healthy; API readiness reports schema 0007, Redis ok, explicit fake provider, and frontend HTTP 200.

- Gateway Docker build and Caddy validation passed, with local brand/font/license checks and byte-exact HTTP SPA/font checks in a temporary loopback-only container. An initial HTTP probe raced startup; bounded readiness retries passed. Existing Caddy indentation warnings remain nonfatal.
- Source checkpoint: `89a062f0e0507f031ad973193d867b3462c078d9`, local branch `codex/tarvio-frontend`. See [current frontend evidence](evidence/tarvio.json); unrelated untracked `skills/` was preserved.

No blocker is known for the local deterministic-provider integration. Physical-device
keyboard behavior, live-provider validation, independent human evaluation and off-host
encrypted restore remain unverified release boundaries. Earlier benchmark/release/video
evidence remains tied to its own pre-Tarvio revision; no new performance target is claimed.
Run `bash scripts/start-local.sh` and open `http://localhost:5173`. Next release step:
physical-device keyboard validation, followed by the existing independent release gates.
