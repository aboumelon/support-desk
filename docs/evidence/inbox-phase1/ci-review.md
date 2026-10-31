# Phase 1 CI / regression review — 2026-10-31

Status: **not cleared for merge**. PR #1 remains draft; no Phase 2 work.

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
| Staff login navigation concern | **Unclassified CI failure pending logs**; no new frontend navigation regression reproduced | Login component byte-identical to baseline. New synthetic login→Inbox→detail→Back check passes; existing real workflow strengthened, awaiting backend CI. Backend credentials, rate limiting, Origin and cookies not verified locally. |
| `superseded` vs `succeeded` concern | **Test race candidate**, not a confirmed CI diagnosis | Existing test waits for an AI draft then clicks handoff. Fake provider defaults to `normal` (10ms chunks), while documented browser regression command requires `FAKE_SCENARIO=slow` (150ms). CI does not set it. Only queued/running runs are superseded; an already succeeded run is correctly not rewritten. All relevant backend/test/workflow code predates Phase 1. No backend behavior, provider fixtures or assertions changed. |
| Missing new-conversation control concern | **Unclassified CI failure pending trace/HTTP evidence** | Control remains customer-only; staff cannot create conversations. Customer desktop list has control; narrow detail intentionally hides list until Back. New fixture checks at390/1365 pass creation navigation. Cannot infer CI cause (wrong audience/failed bootstrap/rate limit/etc.) without trace. |
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
