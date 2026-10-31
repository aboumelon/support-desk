# Final Phase 1 CI stabilization

Review PR #1 only. No merge or Phase 2. This record supersedes the earlier investigation's
pending proposals; it does not relabel historical failed runs as successful.

## Root cause and ordering

The normal fake provider yields 24-character chunks with 10ms spacing. The worker checks
lease/epoch before publishing each provisional `ai.delta`. After iterator exhaustion it
records usage and calls the real finalizer, which can commit an assistant message and mark
the run `succeeded`. The UI showing a provisional draft is not a synchronization barrier:
the worker may finish between that render and the browser's handoff request. Handoff
correctly supersedes only queued/running runs, not an already succeeded run. Broadening
the expectation to accept success would stop testing cancellation.

## Deterministic cancellation proof

Only the dedicated test worker (`tests.e2e_worker:app`) installs a wrapper around the
ordinary fake iterator and generation function. Its guarded entrypoint requires
APP_ENV=test, LLM_PROVIDER=fake and an explicit existing IPC directory. Normal dev and
production entrypoints, all `src/supportdesk` production code, API contracts, finalization
and cancellation semantics are untouched. `tests/` is absent from the production Docker
image and application wheel. There is no HTTP test-control endpoint.

Each cancellation attempt uses a fresh random marker plus an arm file. Unmarked or
unarmed requests use the ordinary fake stream unchanged. The test:

1. Waits for websocket connection and a real Redis draft subscriber.
2. Sends the marked question through the real customer composer/message endpoint.
3. Waits for `paused`, written only after the worker consumes and publishes the first
   normal provider delta and requests another. No subsequent chunk/final message can
   complete while this barrier is held.
4. Requires a visible provisional draft and snapshot status **running**.
5. Clicks the real UI handoff control and requires the original **superseded** status.
6. Releases the iterator in `finally`, even on test failure, and waits for `finished`,
   written after the original generation/finalization call exits.
7. Again requires **superseded**, zero persisted assistant messages and no barrier timeout.

The finalizer therefore sees the real cancelled lease/changed epoch and must reject the
obsolete output. It is not patched to return a successful cancellation result. A bounded
45s watchdog raises and records `timed-out`; the test explicitly rejects this signal, so
expiry cannot substitute for the browser handoff. The 10ms IPC poll is condition polling,
not a sleep chosen to race the provider. Standard-library unit tests cover the production/
live guards, first-delta/pause/release ordering and timeout failure.

## Rate-limit-safe orchestration

`public/demo` and public visitor-session creation share the unchanged server-side
`session` bucket: 5 attempts per 60s per real remote identity. Multiple isolated browser
contexts still share the CI runner's identity, so independent test sessions alone do not
isolate that quota. Fast tests can exhaust it and then falsely report missing controls.

Real-backend test contexts now serialize public session creation through a private ledger.
After each request completes, at least 13s elapse before the next starts. Six attempts span
at least 65s; at most five fall in any 60s interval. The ledger persists between test files,
all three suite invocations and the CSP invocation. The existing single-worker setting is
required. Each Actions job has an isolated database and ledger. The additional guest
browser context and direct API demo bootstrap use the same scheduler.

Requests still reach the real server with their real cookies, Origin and remote identity.
No quota records are cleared, limit raised, client address spoofed, session fixture shared
across tests or 429 retried. Failed admissions count in the ledger too; actual error
responses are forwarded and HTTP200 remains mandatory. Tests await the actual bootstrap
response **before** checking route/UI readiness, rather than treating intentional quota
scheduling as a UI timeout. Existing UI assertions and their timeouts are retained.

## Additional full-suite synchronization uncovered during repetition

At811f54f the push run's first full suite passed, while the PR run failed the pre-existing
manual retry assertion: after an intentionally lost HTTP response, realtime-triggered
snapshot reconciliation correctly acknowledged the committed message and removed Retry
before Playwright clicked it. This is not changed product delivery semantics.

The test now gates delivery of real snapshot responses for that conversation until the
manual second POST is observed, releasing in `finally`. It still drops only the first
HTTP acknowledgement, still submits through the UI, and still requires identical client
message IDs on at least two attempts and exactly one durable message. No canonical
response data is mocked or rewritten. This explicitly models lost acknowledgement *and*
delayed reconciliation, which is the precondition for testing a user-initiated retry.

## Reproduction

Use a dedicated local PostgreSQL database/Redis instance or isolated CI services, never
production data/traffic. Seed and migrate once as in the browser workflow. Example after
configuring those disposable services:

```sh
export APP_ENV=test LLM_PROVIDER=fake
export DATABASE_URL='postgresql+psycopg://supportdesk:local-development-only@127.0.0.1:55432/supportdesk_browser_test'
export REDIS_URL='redis://127.0.0.1:56379/14'
export ALLOWED_ORIGINS='["http://localhost:5173","http://localhost:5184"]'
export E2E_BARRIER_DIR="$PWD/.local/e2e-barriers"
export E2E_QUOTA_LEDGER="$PWD/.local/e2e-admission/last-completed"
bash scripts/e2e-dev.sh
# In another shell with the same environment, after wait_demo succeeds:
PLAYWRIGHT_OUTPUT_DIR=test-results/full-1 pnpm --filter @supportdesk/web test:e2e
PLAYWRIGHT_OUTPUT_DIR=test-results/full-2 pnpm --filter @supportdesk/web test:e2e
PLAYWRIGHT_OUTPUT_DIR=test-results/full-3 pnpm --filter @supportdesk/web test:e2e
pnpm build
pnpm --filter @supportdesk/web preview:csp
# With the built frontend preview running:
PLAYWRIGHT_OUTPUT_DIR=test-results/csp CSP_BASE_URL=http://localhost:5184 pnpm --filter @supportdesk/web test:e2e e2e/production-csp.spec.ts
```

The ordinary suite's existing conditional CSP skip is retained because that test targets
the separate built frontend server. It is subsequently executed explicitly, not omitted.
Outputs for all repetitions/CSP are preserved separately. No retries are added.
Later repetitions and CSP run even if an earlier suite fails, provided stack readiness
succeeded and the job was not cancelled. Failed steps still fail the job; there is no
continue-on-error or hidden/red-to-green conversion.

## Verification results

Pending completed full-suite repetitions and separate CSP result; see the PR's latest
Actions checks. Do not infer green CI from the mechanism or from the focused unit checks.
The local sandbox cannot run PostgreSQL/backend; integrated evidence must come from CI.
Raw Actions log/trace artifact download hosts remain blocked here; API-visible GitHub
assertion annotations and named-step conclusions are available and are used for results.
