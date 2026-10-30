# Tarvio frontend integration

## Shared customer entry (2026-10-30)

Home now places a customer entry beside staff login. The optional backend-confirmed
`customer_entry_key` links the seeded shared workspace; no key is guessed during
capability failures or missing fixtures, and production omits it. Persian copy explains
that customer/staff entry shares the main workspace while each independent demo has
its own workspace. Buttons wrap on intermediate widths and stack on mobile.

Focused verification passed: 16 PostgreSQL identity/capability/portfolio cases, two
browser cases (real shared customer-to-fixed-staff messaging, plus capability-disabled
and retry states), seven frontend unit cases, Ruff, mypy, frontend lint/types/format,
contract regeneration/drift and production build. The customer-to-staff browser case
queues the conversation before sending and asserts no AI run, consuming no live quota.
Landing screenshots were captured at 1440/1366/390/320; desktop/mobile were visually
inspected. Prior UI edits and all historical evidence were preserved. Current screenshots
are under `evidence/customer-entry-20261030/`; exact commands are in progress.md.

## Current portfolio revision (2026-10-30)

The current implementation retains the visual system, local fonts, route boundaries,
source sheets and responsive panes from the original integration below. Current changes:

- Inbox queries use authorized backend text/reference search and opaque page cursors;
  first-customer-message titles and last-message previews are persisted-data read models.
  No loaded-row total or invented customer name is shown.
- `/app/$workspaceId/settings` redirects to Knowledge. Only Knowledge owns activation;
  the rail contains Inbox and Knowledge plus the existing audience/logout controls.
- Entry reads minimal public capabilities and handles disabled demos, loading and retry.
  The single compact indicator separates fictional data from simulated/live/disabled AI.
- Copy is shorter and remains centralized in `locales/fa.json`. The landing scene is
  explicitly illustrative. Fictional fixtures now use Tarvio Cloud.
- Direct/expired/unauthorized routes, server search beyond the first 50 conversations,
  separate audience logout, capability failures and disabled-entry behavior have fresh
  browser coverage alongside the existing real messaging/knowledge/recovery flows.

Fresh verification: 8/8 browser cases passed in 1.9 minutes; 7/7 frontend unit cases,
lint, TypeScript, formatting, generated-contract drift and production build passed.
The final responsive-only rerun passed in 25.0 seconds after the title-direction and
short search-placeholder adjustment. PostgreSQL/Redis/Celery and pinned E5 were real;
answer generation was explicitly simulated. Two capability-display cases stub only
the capability response, not chat or persisted application data.

Current evidence: [portfolio manifest](evidence/portfolio.json),
[progress and exact commands](progress.md), [provider/deployment handoff](portfolio-release.md).
Current images are kept separately under `evidence/portfolio/`; the historical images
and manifests below are retained unchanged.

| View | Desktop | Tablet | Narrow tablet | Mobile |
| --- | --- | --- | --- | --- |
| Operator | [1440](evidence/portfolio/operator-1440.png) | [1024](evidence/portfolio/operator-1024.png) | [768](evidence/portfolio/operator-768.png) | [390](evidence/portfolio/operator-390.png) |
| Customer | [1440](evidence/portfolio/customer-1440.png) | [1024](evidence/portfolio/customer-1024.png) | [768](evidence/portfolio/customer-768.png) | [390](evidence/portfolio/customer-390.png) |
| Knowledge | [1440](evidence/portfolio/knowledge-1440.png) | [1024](evidence/portfolio/knowledge-1024.png) | [768](evidence/portfolio/knowledge-768.png) | [390](evidence/portfolio/knowledge-390.png) |
| Source | — | [1024](evidence/portfolio/source-1024.png) | [768](evidence/portfolio/source-768.png) | [390](evidence/portfolio/source-390.png) |
| Entry | [1440](evidence/portfolio/entry-1440.png) | — | — | [390](evidence/portfolio/entry-390.png) |
| Login | [1440](evidence/portfolio/login-1440.png) | — | — | [390](evidence/portfolio/login-390.png) |

Rendered desktop and mobile screens were inspected, including tablet breakpoints,
source focus/backdrop and full-page Knowledge. Full-page captures show the fixed
mobile rail at the original viewport boundary. A reduced 390×520 viewport/focused
composer is browser emulation; a physical mobile keyboard remains unverified.

## Historical prototype integration (2026-10-29)

Status at the checkpoint below: connected implementation, local browser workflows and container assets verified.
Source archive: `/home/armin/Downloads/Tarvio Support Workspace Prototype (1).zip`.
SHA-256: `acd8125df385d0ed1023d778946b5807bddaf982d3322360acf3c3b5b854a8c4`.
Reference extracted under ignored `.local/references/tarvio-latest/`. Its configuration,
agent instructions and simulated business logic are not application inputs.

## Migrated application

One React/Vite application remains under `apps/web`, using the existing TanStack
Router/Query, i18next and generated API client. Prototype package/build/Figma files
were not adopted; Vite remains 7.3.7. All product copy is in `locales/fa.json`.

- `main.tsx`: authenticated route boundaries, workspace membership, separate audience sessions and navigation rail.
- `features/auth/pages.tsx`: entry/demo and real staff login, loaded as a separate route chunk.
- `features/conversation/desk.tsx`: paginated inbox, ownership controls, scoped composer and responsive panes.
- `use-conversation.ts`: snapshots/history, retained event pagination, durable sends/retries, realtime/polling and provisional AI state.
- `timeline.tsx`: sequenced persisted messages/transitions, scroll anchoring and citations.
- `source-inspector.tsx`: authorized citation retrieval, desktop aside and accessible narrow-screen dialog.
- `features/knowledge/knowledge.tsx`: real ingestion, version replacement, document withdrawal and canonical assistant activation.
- `components/ui.tsx`: shared Tarvio brand/icons/buttons/modal; scoped `styles/app.css` provides ink/cobalt tokens and responsive layouts.

All existing routes remain: `/`, `/demo`, `/login`, `/workspace`, `/chat/$publicKey`,
`/app/$workspaceId/inbox`, `/app/$workspaceId/conversations/$conversationId`,
`/app/$workspaceId/knowledge`, and `/app/$workspaceId/settings`. Direct conversation
refresh restores authorized history; settings shows the real assistant setting.

## Contract decisions

- Backend `bot` maps to the assistant responsibility presentation; assignment uses the authenticated actor and `assigned_actor_id`.
- Conversation/customer names and subject previews are absent. Use a generic customer label and short real UUID reference.
- Message role/time/order come from `sender_kind`, `created_at` and `event_seq`.
- Timeline reads the existing authorized, paginated event API. Existing events without actor/action remain generic; no invented people or dates.
- Newly persisted control events include additive `action`, `actor_id`, `actor_kind` payload fields so later history distinguishes acceptance, release and handoff. No schema/migration/ownership policy changes.
- Knowledge uses `active_version_id` and document-level withdrawal, independently showing the latest processing version.
- Source selections include audience/workspace/conversation/message/label and retrieve authorized citation content.

## Verification

Commands run from the repository root on 2026-10-29:

```bash
pnpm lint
pnpm typecheck
pnpm exec prettier --check apps/web/src apps/web/e2e apps/web/index.html apps/web/package.json
pnpm --filter @supportdesk/web test
pnpm contracts:check
pnpm build
FAKE_SCENARIO=slow bash scripts/start-local.sh
pnpm --filter @supportdesk/web test:e2e
bash scripts/start-local.sh
```

Lint, types, formatting, generated-contract drift and production build passed. Seven
frontend unit cases passed. The final browser sweep passed **5/5 in 1.4m**, using the
real local PostgreSQL, Redis, FastAPI, outbox dispatcher, Celery ingestion and pinned E5.
The deterministic backend LLM was explicitly selected; no frontend fixture responses
or live calls were used. The slow-provider setting exercised handoff during generation
and was removed by restarting the ordinary local supervisor after the tests.

Browser coverage includes:

- Isolated demo/customer/staff sessions, staff login, direct public entry and conversation refresh.
- Two conversations, independent persistent drafts, queue filters, real sends and offline replay/polling recovery.
- Handoff during streaming, claim/reply/release/resolve/reopen, canonical persisted transitions and 105 control events across multiple 100-event pages.
- A response dropped after actual server commit, followed by retry with the same UUID and exactly one persisted message.
- Actual upload/ready processing, assistant activation on/off persisted by PUT, failed replacement with the previous active version still usable, document withdrawal and citation unavailability.
- Non-admin knowledge restrictions, messages assigned to another operator, and cross-workspace 404 boundaries.
- Operator/customer/knowledge at 1440, 1024, 768 and 390px; no horizontal page overflow. Source failures/retry and modal focus containment, inert background, Escape and trigger focus restoration. A 390x520 focused-composer case covers reduced available viewport height.

Backend focused verification passed **7 PostgreSQL ownership/messaging/history tests in
1.37s**, including retained and fully expired event history and cross-workspace access.
The final complete backend suite passed **42/42 in 136.93s**, including worker-crash
and lease recovery. Ruff formatting/lint passed; configured strict mypy passed 54 files.

```bash
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked --project apps/backend --all-extras pytest -q apps/backend/tests
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked --project apps/backend ruff format --check apps/backend
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked --project apps/backend ruff check apps/backend
cd apps/backend
UV_CACHE_DIR=/tmp/supportdesk-uv-cache uv run --locked mypy src
```

One chained verification command ended with SIGTERM after pytest and Ruff had passed.
A subsequent root-directory mypy invocation did not load the backend configuration
and reported an untyped Celery import; it was stopped and rerun successfully from
`apps/backend` using the documented command above.

The source checkpoint is `89a062f0e0507f031ad973193d867b3462c078d9` on the local
`codex/tarvio-frontend` branch. Container build and inspection passed:

```bash
docker build --label org.opencontainers.image.revision=89a062f0e0507f031ad973193d867b3462c078d9 -f apps/web/Dockerfile -t supportdesk-gateway:tarvio .
docker run --rm --network none --entrypoint caddy supportdesk-gateway:tarvio validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Image ID: `sha256:b35a9df1f5f620b304cbe51c2642f045a188773859e87a46d964fc7be5439342`.
A temporary container bound only to `127.0.0.1:5181` served a direct SPA route and
the local Persian WOFF2 font byte-for-byte equal to the production build; both font
licenses, brand SVG and absence of Google Fonts CSS URLs were checked inside the image.
The container was removed afterward. The first HTTP probe raced startup and reset;
retrying with bounded readiness retries passed. Caddy's existing indentation warning
is nonfatal; its configuration validated. Backend proxy/realtime configuration is unchanged.
This is a local asset check, not a public deployment or a full container-stack release.
Machine-readable hashes and verification boundaries: [tarvio.json](evidence/tarvio.json).

Production build uses local font assets and license files and emits an approximately
415 KiB main JavaScript chunk, with auth, knowledge and conversation code split out.
Rollup reports two upstream Zod pure-comment annotation warnings; the build succeeds.
This is build-size evidence, not a browser performance measurement.

Intermediate failures were corrected and rechecked: source button accessible name,
withdrawn citation 410 rendering, Shift+Tab containment, the asynchronous activation
checkbox state, and index HTML formatting. An auxiliary screenshot script initially
selected the hidden mobile marketing heading; it was corrected to select a visible
heading and all four entry/login screenshots were captured.

## Screenshots

Images were captured from real local application data and visually inspected. The
fictional Naran document titles/content are persisted backend demo fixtures, not new
frontend identities. Knowledge full-page captures include the fixed mobile rail at
the original viewport boundary; the page itself scrolls independently.

| View | Desktop | Tablet | Narrow tablet | Mobile |
| --- | --- | --- | --- | --- |
| Operator | [1440](evidence/tarvio/operator-1440.png) | [1024](evidence/tarvio/operator-1024.png) | [768](evidence/tarvio/operator-768.png) | [390](evidence/tarvio/operator-390.png) |
| Customer | [1440](evidence/tarvio/customer-1440.png) | [1024](evidence/tarvio/customer-1024.png) | [768](evidence/tarvio/customer-768.png) | [390](evidence/tarvio/customer-390.png) |
| Knowledge | [1440](evidence/tarvio/knowledge-1440.png) | [1024](evidence/tarvio/knowledge-1024.png) | [768](evidence/tarvio/knowledge-768.png) | [390](evidence/tarvio/knowledge-390.png) |
| Source dialog | — | [1024](evidence/tarvio/source-1024.png) | [768](evidence/tarvio/source-768.png) | [390](evidence/tarvio/source-390.png) |
| Entry | [1440](evidence/tarvio/entry-1440.png) | — | — | [390](evidence/tarvio/entry-390.png) |
| Login | [1440](evidence/tarvio/login-1440.png) | — | — | [390](evidence/tarvio/login-390.png) |

## Reliability and corrections

- Entry/login, authenticated route navigation, rail, responsibility strip, sequenced message/event timeline, source inspector and admin knowledge UI are connected to real application APIs.
- Fonts: pinned `@fontsource-variable/estedad` / `@fontsource-variable/inter` 5.3.0, served locally; OFL licenses copied into public font assets.
- Retry uses persistent IndexedDB identities plus a shared in-flight guard. Composer drafts and selected conversations are scoped by audience/workspace/actor/conversation.
- Modal source sheets use a native dialog plus explicit focus trapping, inert background, Escape and trigger focus restoration. Desktop source inspectors remain nonmodal.
- Citation 410 is treated as an unavailable source, distinct from a transport failure. Cached excerpts are hidden while access is being revalidated.
- Legacy timeline events use persisted transitions; new control events carry actual action/actor metadata. Event reset responses now include the oldest retained sequence, allowing authorized recovery with an explicit retention notice, including when all events expired.
- Assistant activation reflects the pending choice while saving, then uses the canonical response; failures restore the last confirmed setting. Rendering never changes server settings.
- File constraints follow the existing backend: TXT, Markdown or text PDF, maximum 10 MiB. Replacement is a new processing version; withdrawal affects the whole document.
- Safe react-markdown rendering remains in place, with external images rendered as alt text, unsafe links/HTML blocked and code laid out LTR.

## Remaining boundaries and next step

No known blocker remains for this local deterministic-provider integration. Real mobile
keyboard behavior still merits a physical-device pass; browser viewport/focus emulation
does not prove OS keyboard behavior. Public deployment, live-provider validation,
independent human evaluation and off-host encrypted restore remain the previously
recorded release gates. Prior benchmark/release/video manifests refer to their own
pre-Tarvio revisions and are not fresh performance evidence for this UI.

Run `bash scripts/start-local.sh`, open `http://localhost:5173` and start an isolated
demo. The next release step is the physical-device pass followed by the separate
release gates above. No push, public deployment, paid service or live credential change
was performed.
