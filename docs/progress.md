# SupportDesk implementation progress

Last updated: 2026-10-29 (Asia/Tehran). Authority: [original design](../supportdesk-system-design-v1.md).

## Completed and verified

- Root established directly at `/home/armin/projects/support-desk`; original design and unrelated `skills/` preserved.
- M0: locked Python 3.13 / Node 24 monorepo; validated config; Alembic; fictional seed; separate opaque staff/customer sessions; CSRF/origin/rate limits; isolated expiring demo workspaces; tenant tests; CI definition.
- M1: atomic message/event/outbox writes; actor/client-ID retry/conflict behavior; command receipts; consistent snapshots; pagination; monotonic read cursors. PostgreSQL concurrency tests and browser refresh persistence pass.
- M2 core gates: competing claims; real two-API delivery; lost final notification repaired without a later event; reconnect replay; bounded sender; inbox/ownership UI. Real Redis/Celery ingestion and duplicate dispatch also verified.
- M3 core: private bounded uploads, immutable versions, ready-only pgvector retrieval, replacement-pending and withdrawal behavior. Pinned E5 revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`; actual CPU inference produces 384 dimensions.
- M4 core: explicit fixture/live adapters, provisional drafts, citations, conservative usage reservations and bounded retries. Fake-provider tests cover handoff, superseding turns, withdrawal, source replacement, stale leases, invalid citations, budgets and unknown timeout/429/drop usage.
- Full serialized backend suite: **34 passed in 161.91s**. Subsequent focused checks passed: 12 assistant cases including exhausted-crash recovery, five identity cases, two configuration cases and 200-event replay below three seconds.
- Frontend: ESLint, strict TypeScript, four realtime/Markdown safety unit tests, generated contract drift check and production Vite build passed. Route splitting reduces the main bundle below 500 KiB.
- Playwright: isolated customer/operator contexts completed assistant answer/citation, handoff, claim/reply and refresh persistence; **2 passed in 14.1s**, including direct staff login and public customer chat preserving the actor after refresh. Customer/operator/knowledge screenshots are in `docs/evidence/`.
- API, gateway and CPU worker container builds passed. Non-root worker app startup/E5 inference and Caddy validation passed. Production Compose configuration validation passed without deployment.
- Restore drill: PostgreSQL restored to `supportdesk_restore_test`; all **10 referenced artifact hashes** matched a separate file copy. Off-host encrypted restore remains unverified.
- Forty-case fixture evaluation: recall@5 **1.0**, fixture handoff **0.975**, zero source-isolation failures, valid source IDs. Original threshold-only handoff was **0.625**; both reports are retained. Human faithfulness ratings and a fresh blind evaluation are uncollected.

## Implemented but awaiting final verification

- Assigned/unread inbox filters, expiry cleanup, source/config changes, health degradation and bounded operational metrics have been implemented; final regression sweep pending.
- Light API/dispatcher and CPU worker Docker targets, private production Compose, Caddy, runtime-role SQL and runbook. Production Compose has not been deployed.
- The corrected full load run passed: 200 connections, two APIs, 3,194 commands, zero failures, p95 commit 92.36 ms and p95 delivery 430.05 ms. See `evidence/benchmark.md`.

## Honest failures and corrections

- Initial SQLAlchemy asyncio dependency, migration constraint naming and model-discovery errors were corrected and migrations rerun. Migrations 0006/0007 retain upgrade continuity.
- Initial Playwright attempts failed while standalone API/worker processes had stopped. A local supervisor now keeps the demo roles together; the subsequent flow passed.
- First full 200-client benchmark failed: p95 message commit about 50 seconds and p95 delivery about 113 seconds, with 483 send failures. Evidence is retained in `benchmark-before-fixes.json`.
- Fixes: notify only matching subscriptions; drain outbox in batches; evaluate message quotas within the current DB transaction. Short 200-client rerun had **zero send errors**, p95 commit **276 ms**, p95 delivery **1.21 s**. Idle dispatcher polling was then reduced to 250 ms before the full corrected rerun.
- Git metadata was initially empty/inaccessible. Authorized local `git init` succeeded outside the restricted mount. The source checkpoint, including both lockfiles, is being prepared after final evidence updates. No remote push or deployment has occurred.

## Remaining release gates / limitations

- Full healthy-load targets and 200-event replay passed. Actual Redis outage/restart and Celery SIGKILL/lease-expiry/queue-reconstruction tests passed separately. Combined degradation under the full 200-client workload remains a broader resilience check; performance targets are not capacity guarantees.
- Record final source commit and tree/lockfile/image hashes; verify the final prefixed broker regression and final source checkpoint.
- PDF page/OCR/byte/encoding and real E5 chunk-window checks passed. Broader PDF fuzzing and multi-tab UI receipt/presence coverage remain useful release-hardening checks.
- Retention schedules now cover messages, citations, events, commands, audits, outbox, eligible jobs, withdrawn chunks, demo expiry and orphan files. AI job identity tombstones have an explicit ADR exception. Full operational job/outbox/AI metrics, independent deployment restore timing and production scheduling remain release operations.
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

Finish the prefixed broker regression, freeze the source checkpoint, record final verification
and image/lockfile hashes, and leave the supervised demo running at http://localhost:5173.
A public-release claim still requires the external/unverified gates listed above.


## Final failure/recovery evidence additions

- Actual Redis service outage/restart: two network reliability tests passed in 38.49s; human REST chat and periodic repair survived.
- Actual Celery SIGKILL, unmodified lease-clock expiry and broker reconstruction plus parser limits: four checks passed in 85.45s.
- One full test invocation overlapped a separate fixture-truncating test invocation, causing test-database interference. A session-wide PostgreSQL advisory lock now serializes pytest invocations; the subsequent full suite passed.
- Safe Markdown disables raw HTML and unsafe URL schemes, with passing renderer tests. Public/staff routes and canonical assistant-setting bootstrap are implemented.
- Demo recording: `evidence/demo.webm` (26.52 seconds, automated real customer flow). Screenshots and the longer manual walkthrough are linked from README.
