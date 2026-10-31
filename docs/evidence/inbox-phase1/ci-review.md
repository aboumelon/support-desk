# Phase 1 CI / regression review — 2026-10-31

Historical investigation status: blocked at the revisions recorded below. The subsequent
[final stabilization record](stabilization.md) supersedes these pending CI proposals and
records six full-suite passes plus separate CSP passes. PR#1 remains draft/unmerged; no
Phase2 work.

## Compared revisions and evidence availability

- Exact main baseline `a075b6fcac1c2ccd18450e336d670ec5de2f34a0`:
  [browser-flow 41084628576](https://github.com/aboumelon/support-desk/actions/runs/41084628576), failed.
- Earlier main `9dc3bf97b4961c8e624ddcbb19e2b71e8f9beed2`:
  [41083301354](https://github.com/aboumelon/support-desk/actions/runs/41083301354), failed.
- Original Phase 1 `8f939387600e55a70826bf4cab6f78f1e9782b1e`:
  [PR run 41200608501](https://github.com/aboumelon/support-desk/actions/runs/41200608501)
  and [push run 41200591230](https://github.com/aboumelon/support-desk/actions/runs/41200591230), failed.

GitHub API metadata shows failure in the combined `Run mkdir -p .local` step
(start dev stack, wait for demo, run Playwright); setup/seed steps succeeded and the
subsequent production-CSP step was skipped. Foundation checks passed on main and PR.
This does **not** prove the same individual tests failed on both revisions.

Attempted `gh run view --log-failed` for all four runs and `gh run download` for the
PR's `browser-evidence`. Downloads redirect to `results-receiver.actions.githubusercontent.com`
and Azure blob hosts outside this sandbox's permitted outbound hosts, and terminate
with EOF. Artifact metadata confirms all four artifacts exist and are unexpired.
Check annotations contain only exit code 1, Node-action deprecation and runner-image
migration notices; check summary/text are empty. The unauthenticated GitHub page also
requires sign-in to view logs. **Original CI log contents and CI Playwright traces
have not been inspected.** No conclusions below pretend otherwise.

A GitHub Playwright reporter is added alongside normal line reporting on Actions.
It preserves all assertions/timeouts/retry settings and should expose future failure
assertions through accessible check annotations. It does not retroactively recover
original traces. Original artifacts still need inspection by an environment that can
download them, or attachment of their extracted logs/error contexts/traces here.

## Classification and focused findings

| Item | Classification / confidence | Evidence and action |
| --- | --- | --- |
| Staff source layout at 1200–1439px | **New regression, confirmed and fixed** | Actual frontend geometry plus main-CSS comparison; see measurements below. Reuse existing staff source dialog below1440. |
| Staff login navigation concern | **Pre-existing test synchronization race**, fixed; see fresh-CI sections | Login component byte-identical to baseline. New synthetic login→Inbox→detail→Back check passes; existing real workflow strengthened, awaiting backend CI. Backend credentials, rate limiting, Origin and cookies not verified locally. |
| `superseded` vs `succeeded` concern | **Pre-existing test flakiness/race**, reproduced in fresh CI | Existing test waits for an AI draft then clicks handoff. Fake provider defaults to `normal` (10ms chunks), while documented browser regression command requires `FAKE_SCENARIO=slow` (150ms). CI does not set it. Only queued/running runs are superseded; an already succeeded run is correctly not rewritten. All relevant backend/test/workflow code predates Phase 1. No backend behavior, provider fixtures or assertions changed. |
| Missing new-conversation control concern | **Test infrastructure/environment**, confirmed rejected bootstrap (HTTP429) | Control remains customer-only; staff cannot create conversations. Customer desktop list has control; narrow detail intentionally hides list until Back. New fixture checks at390/1365 pass creation navigation. Cannot infer CI cause (wrong audience/failed bootstrap/rate limit/etc.) without trace. |
| Historical main browser-flow failure | **Pre-existing CI failure at run level only**, individual defect(s) unknown | Exact parent already fails the combined browser step; no assertion-level attribution possible from metadata. |
| Historical log/artifact retrieval | **Review environment issue, confirmed** | Redirect hosts blocked; not evidence that GitHub's runner environment caused the E2E failures. |

Do not relabel all CI failures as pre-existing simply because main is red. Node action
and Ubuntu notices are warnings, not established causes. No assertion was broadened,
no test skipped, no retry added and no existing fixture changed to obtain green checks.

## Source layout reproduction / fix

Actual React frontend using intercepted synthetic sessions, snapshot and citation API
responses; no real source authorization/retrieval claim. A temporary measurement
harness replaced the stylesheet with `git show a075b6f:apps/web/src/styles/app.css`.
The source component was unchanged at measurement time. This is a **CSS-baseline
comparison**, not a full authenticated execution of main.

| Viewport | Main CSS, source open: conversation | Original Phase 1, source open | Phase 1 fixed, source dialog open |
| --- | ---: | ---: | ---: |
| 1200 | 556px | 492px | 812px |
| 1280 | 636px | 572px | 892px |
| 1365 | 667px | 657px | 977px |
| 1439 | 741px | 731px | 1051px |

Original Phase 1 loses 64px versus main at1200/1280 and 10px at1365/1439. Below1281,
legacy fixed-position source CSS also reserves a phantom third grid column: inherited
technical debt worsened by the new index strategy. Four new geometry assertions failed
before the fix (expected812/892/977/1051, observed492/572/657/731). Inspected the local
pre-fix Playwright trace's action/error records; these are **local regression traces,
not the unavailable CI traces**. All four assertions pass after the staff-only fix.

Minimal fix: existing source dialog for staff <1440; existing aside ≥1440; matching
staff grid boundary. Customer source breakpoint remains1200; no source redesign,
new panel, API change or later-phase 360px aside styling. Added1439/1440 transition
coverage for citation selection, draft, reader anchor, Escape and trigger focus.

## Verification and remaining gates

Local: 23 frontend-fixture Playwright tests, 25 unit tests, typecheck, lint and production
build passed. Third-party Zod PURE annotation build warnings remain non-blocking.
The existing real authenticated customer/operator workflow now additionally checks staff
conversation routing,1119/1120 transitions, Back, draft and unchanged authenticated scope.
No extra demo bootstrap or seed data was added to that shared-backend suite.

Local Docker/uv/backend remain unavailable. Synthetic login/creation tests establish
frontend navigation only, not real authentication, session security or persistence.
Original CI artifacts and a fresh backend-integrated CI result remain blocking evidence.


## Fresh integrated CI at 698a3c7 — assertion-level evidence

The added reporter made failure assertions available through GitHub check annotations:

- [PR run 41202784838](https://github.com/aboumelon/support-desk/actions/runs/41202784838),
  job124541745719: **31 passed,1 failed,1 skipped**. Only failing test:
  `tarvio.spec.ts:50`, expected `superseded`, received `succeeded` (5s poll timeout).
- [Push run 41202781451](https://github.com/aboumelon/support-desk/actions/runs/41202781451),
  job124541734693: **31 passed,1 failed,1 skipped**. Only failing test:
  `customer-entry.spec.ts:78`, expected `/app/undefined/inbox`, actual a valid UUID
  workspace Inbox. The Tarvio supersession test **passed on this identical commit**.
- Foundation passed. The skipped production-CSP test is the existing conditional skip
  in the ordinary dev-server suite; its separate production step was not reached because
  the preceding suite failed. No skip was added by this review.

Consequently the standalone staff-login test and the strengthened real authenticated
customer/operator workflow **passed in both fresh CI runs**, including new1119/1120,
route/Back/draft/session-scope assertions. This is real CI/backend evidence, distinct
from local intercepted-session checks. It is not a claim that every authenticated
workflow passed: the broad Tarvio scenario stops early in the failing PR run.

### Revised classifications

1. **Supersession expectation: pre-existing test flakiness/race, confirmed timing-sensitive.**
   Same test passes/fails on the same commit. Backend supersession only changes queued/
   running runs; fake-provider normal completion can win against UI handoff. Test,
   provider, default config and CI startup predate Phase1. The original main traces are
   still unavailable, so this does not establish which assertion failed on main.
   No change to `superseded` expectation, assistant-message-count assertion, provider
   scenario, backend finalization or fixtures is made. A deterministic cancellation
   barrier (or a separately approved CI configuration matching the documented slow
   scenario) remains needed; merely accepting `succeeded` would invalidate the test.
2. **Customer-entry “staff login” failure: pre-existing test synchronization race.**
   Its source is byte-identical to main. It awaits URL navigation, then immediately
   reads `/customer/session` while `CustomerEntry` is still doing GET/visitor-session
   POST. The API error body lacks workspace_id, producing `/app/undefined/inbox`;
   staff login itself reaches a real authorized Inbox. Fixed test readiness only:
   wait for the existing new-conversation control, explicitly require HTTP200 and
   a UUID workspace identity, then retain the exact staff URL and all conversation/
   reply assertions. No fixed fixture, arbitrary sleep, retry, selector relaxation,
   backend or product behavior change.
3. **Missing new-conversation controls:** not a failure in either fresh run. Local
   fixture creation checks and the real integrated customer/operator flow pass.
   Original-run trace still needed to attribute any historical occurrence. Absence
   of the control before visitor bootstrap completes is not an Inbox navigation bug.
4. **Staff source compression:** confirmed new Phase1 regression fixed as above;
   all added source tests passed in both fresh integrated CI suites.

Historical raw log/CI trace retrieval remains blocked. Check annotations establish
these new failure messages and suite outcomes, not network timelines or screenshots.
The original per-failure comparison remains incomplete; do not claim it was inspected.


## Follow-up integrated CI at d7f3504

- [PR41203105529](https://github.com/aboumelon/support-desk/actions/runs/41203105529):
  **30 passed,2 failed,1 existing conditional skip**. Tarvio broad flow never observed
  the ephemeral `ai-draft` (20s); Tarvio responsive flow never reached the bootstrap
  new-conversation control (5s).
- [Push41203102124](https://github.com/aboumelon/support-desk/actions/runs/41203102124):
  **30 passed,2 failed,1 existing conditional skip**. Both responsive and timeline
  tests failed on bootstrap new-conversation control. Broad Tarvio test passed.
- The corrected customer-entry test, standalone staff login and strengthened
  authenticated staff navigation passed both. Foundation passed.

AI-draft non-observation is another fast-provider race candidate: an ephemeral stream
can finish before the browser renders it. Missing bootstrap controls now reproduced
in CI, but the failed assertion alone does not reveal HTTP/bootstrap state. Both demo
and public visitor entry share the same per-remote-identity session quota (5 per60s);
several test bootstraps share the runner. That is an environment/test-isolation
candidate, **not yet proven** by HTTP evidence. No quota or fixture is changed.
Added an explicit bootstrap response/status assertion ahead of the unchanged visible-
control assertion to distinguish rejected bootstrap from actual missing UI. Awaiting
this diagnostic run. All original outcome expectations remain intact.


## Final diagnostic result at 4881745 and merge decision

[PR run41203389410](https://github.com/aboumelon/support-desk/actions/runs/41203389410)
(job124543517063): **30 passed,2 failed,1 existing conditional skip**.
[Push run41203385403](https://github.com/aboumelon/support-desk/actions/runs/41203385403)
(job124543504885): **29 passed,3 failed,1 existing conditional skip**.

The new, stricter bootstrap assertion reports **HTTP429 (`RATE_LIMITED`)** in the
responsive test in both runs and in the timeline test in the push run. Thus the missing
new-conversation control is **test infrastructure/environment: rejected demo bootstrap**,
not evidence that Phase1 removed a customer control. The pre-existing5-per60s shared
session quota and shared runner identity explain why suite pacing can affect admission;
no rate limit or session fixture is bypassed, reset or relaxed here. Exact prior-run
HTTP timelines still require the inaccessible traces. Changing suite timing can expose
this existing coupling, so added fixture tests are not assumed irrelevant to pacing.

The broad Tarvio scenario fails on a never-observed `ai-draft` in the PR run and on
`succeeded` instead of `superseded` in the push run. Its existing fast-stream/cancellation
race remains. Same-code pass/fail evidence is recorded above; the exact provider/network
ordering is not inferred as if a trace had been inspected.

The customer-entry readiness fix, standalone staff login, real authenticated staff
Inbox navigation/resize/draft assertions and all23 frontend fixture checks passed in
both diagnostic runs. No further runtime code changed after698a3c7; subsequent changes
are stronger test synchronization/status assertions and documentation.

**Merge decision: BLOCKED.** No Phase2 and no merge. Before clearing the PR:

1. Obtain original main/PR logs and Playwright traces (or attach extracted artifacts)
   to complete the historical assertion-level comparison; egress currently prevents it.
2. Make cancellation/ephemeral-stream coverage deterministic without accepting
   `succeeded`, skipping the scenario or changing backend run-finalization semantics.
   Any provider/test-environment setup must preserve the intended cancellation contract
   and be justified separately rather than silently swapping fixtures for green CI.
3. Provide rate-limit-aware/isolation-safe backend test orchestration that keeps real
   production quotas intact; prove successful demo bootstrap before UI assertions.
4. Rerun the full backend suite and then the separate production-CSP stage; the latter
   has not run because the earlier suite fails.

Local final checks:23 fixture browser tests,25 unit tests, typecheck/lint pass again;
production build passed after the runtime fix (only third-party Zod comment warnings).
The final follow-up commit is documentation only; statuses above identify the exact
runtime/test revision tested, not a claim of a green latest-head workflow.

## Final stabilization mechanism (results pending)

The cancellation scenario now uses an explicit IPC barrier installed **only** by
`tests.e2e_worker:app` in the dedicated `scripts/e2e-dev.sh` stack. Normal application,
provider, development-worker and production-worker entrypoints are unchanged. The
backend Docker image copies `src/` only, not `tests/`; test controls are not packaged.
Installation rejects anything except APP_ENV=test with LLM_PROVIDER=fake and an explicit
private IPC directory. No HTTP control endpoint, backend schema, cancellation or quota
setting is added. A random per-attempt marker also requires a matching local arm file.

Ordering: the test waits for a connected websocket and real Redis draft subscriber;
the ordinary fake provider emits its first delta; the ordinary generation loop consumes
and publishes it; on the next iterator request the wrapper records `paused` and waits
for `release`. The test requires both that signal and visible provisional output, then
requires the active run to be **running** before clicking the real handoff button.
It retains the exact **superseded** expectation. Finally it releases the provider even
on assertion failure. A separate signal is written after the original generation and
finalization transactions return; only then does the test again require superseded and
zero persisted assistant messages. Thus it tests the real epoch/lease/finalization fence,
not a shortcut returning a fabricated cancelled result. Missing release times out and
fails closed; it never automatically resumes into a successful answer.

Real-backend tests now share a serial admission ledger across browser contexts, direct
API bootstrap, three full-suite invocations and CSP verification. After each public
visitor/demo admission completes (including failures), at least13 seconds must elapse
before another starts: at most5 admissions per any60-second interval. This is documented
quota-aware orchestration, not an assertion sleep. The real HTTP request still reaches
the unchanged rate limiter; errors are forwarded without retry and the explicit HTTP200
bootstrap assertions remain. Client identities, cookies and quota rows are not spoofed,
reset or reused across unrelated tests. One worker is required; fresh CI runners each
have their own database and ledger. The ledger is private/ignored and must not be shared
with unrelated production traffic. Tests without the required ledger/barrier fail rather
than silently running a different scenario.

CI runs the **entire** suite in three separately named steps against the same stack,
then the separate built-production CSP verification. Each invocation retains its own
trace/output directory. Local standard-library barrier tests cover guards, pause/release
and timeout. Integrated results will be recorded below; this section alone is not a
claim of successful CI.
