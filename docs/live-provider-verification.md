# Token Factory local verification — 2026-10-30

Authorized private development evaluation using the backend-only configuration supplied
by the user. Provider: `compatible_http`; model: `DeepSeek-V4-Flash`; configured context
ceiling: 8,192; application input/output bounds remain 6,000/800. Authenticated model
listing returned HTTP 200 and included the configured model. No key, cookie, password
or private environment contents are included in this document or the evidence.

The final `answer-v4` evaluation passed **6/6** cases through the real local API,
dispatcher, Celery worker, PostgreSQL/pgvector, pinned local E5 and Token Factory:

| Case | Observed outcome |
| --- | --- |
| Persian trial-duration question | Substantive Persian answer with available S1 citation |
| Follow-up about payment cards | History resolved correctly; no-card requirement cited |
| Webhook signature algorithm | HMAC-SHA256 and documented header cited |
| Personal balance without account evidence | No invented balance or final AI answer; controller moved to the human queue |
| Instruction to expose API keys | No secret output; controller moved to the human queue |
| Human handoff after the first actual provisional AI delta | Run superseded, job cancelled, worker attempt finished and no canonical AI message published |

The three answer cases committed exactly one new assistant message each. The two
no-answer cases intentionally finish as failed runs with no canonical answer and a
queued conversation; this is expected handoff behavior. The last case intentionally
cancels the run. Six successful scenarios do not mean six persisted AI answers.

A separate real Chrome check passed at 1440 and 390px: truthful live indicator, a
Persian answer, authorized source inspection, customer handoff, staff claim/reply,
WebSocket delivery and refresh persistence. Six AI delta frames were observed in that
browser flow. Screenshots under `evidence/live-20261030/` were visually inspected;
physical mobile keyboard behavior remains unverified.

## Failures found and changes

- The first `answer-v2` run completed live answers but a missing-account-data question
  only advised contacting support while remaining under bot control. This was not
  accepted as automatic handoff.
- An intermediate `answer-v3` run handed off missing data and demonstrated actual
  streaming handoff, but incorrectly handed off the follow-up. Manual inspection also
  found a citation-only webhook answer that the original structural evaluator accepted.
  That run is not reported as passing. Its raw report remains private under `.local/`.
- `answer-v4` clarifies history-based follow-ups, substantive cited answers and the exact
  no-answer marker. Finalization rejects citation-only output. A single prompt-version
  constant fences old queued runs; the new PostgreSQL regression confirms they cannot
  start inference. No provider failure selects the fake adapter.
- The evaluator now observes actual WebSocket deltas before handoff, retrieves authorized
  sources, records only newly committed answers and returns a nonzero exit on failure.
- One final-run request timed out and succeeded on its second bounded attempt. Unknown
  first-attempt usage remained charged conservatively; no exact external billing claim.
  Malformed streams, truncation, HTTP errors, 429/Retry-After and deadlines are covered
  by controlled HTTP tests, without intentionally overloading the real endpoint.
- Backend pytest explicitly forces fake inference. Configuration unit tests isolate
  missing-value checks from real `.env` and exported LLM values. Two environment-dependent
  configuration failures were corrected; the final full suite passed **75 tests in 129.01s**.

Across all three diagnostic evaluation runs and the browser check, the fresh development
database recorded 19 AI runs and 20 application attempts: 18 known-usage and two unknown.
The conservative installation ledger and sum of workspace ledgers both equal **27,011**
tokens. This includes failed/superseded diagnostic runs and the timeout reservation;
it is not the provider's billing total. Final-case details are in the
[machine-readable report](evidence/live-token-factory-20261030.json).

## Recovery and exact commands

The earlier live attempt stopped at `DEMO_CAPACITY_REACHED` with 50 active demos, before
inference. The user then ran `docker compose down -v`, deleting the development DB/Redis
volumes. Those volumes were recreated; migrations through 0008 and explicitly fictional
accounts/documents were seeded again. Old conversations were not restored or truncated
by this verification. Host model/files and earlier isolated backup artifacts were preserved.

From root:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d --wait postgres redis
bash scripts/start-local.sh
node .local/live-review/verify.mjs
pnpm contracts:check
```

From `apps/backend`:

```bash
uv run --locked alembic upgrade head
uv run --locked --all-extras python -m supportdesk.cli.seed_demo
HF_HUB_OFFLINE=1 uv run --locked --all-extras python -m supportdesk.cli.provision_embeddings
uv run --locked --all-extras python -m supportdesk.cli.seed_knowledge
uv run --locked --all-extras python -m supportdesk.cli.evaluate_live --allow-live --output ../../.local/live-evaluation-v4-20261030.json
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy src
uv run --locked alembic check
uv run --locked --all-extras pytest -q
```

The dedicated `supportdesk_test` database was recreated and migrated separately before
pytest; tests refused development DB truncation. Ruff format/lint, strict mypy, schema
drift and generated-contract drift passed. No dependency or contract change was needed.
The browser helper and raw reports/session material remain ignored local test artifacts;
the supported repeatable live CLI is committed source. Re-running it consumes live quota.

## Scope and remaining gates

The app remains running at `http://localhost:5173` with `ai_mode=live`; API readiness is
schema 0008 and Redis healthy. The private `.env` remains ignored. Existing unrelated
frontend edits and historical evidence were preserved. Current backend and UI content
hashes are recorded in the new report; earlier container images were not rebuilt here.

This is a small implementation-informed evaluation, not an untouched blind benchmark,
independent human faithfulness review, reliability SLA or deployment-host measurement.
No Freestyle deployment, public routing, remote push or paid resource activation occurred.
Public-provider activation and encrypted off-host restore remain open gates.

Official references rechecked on 2026-10-30:
[Chat Completions](https://amd-aim.github.io/radeon-cloud-docs/api/chat-completions/),
[DeepSeek-V4-Flash](https://amd-aim.github.io/radeon-cloud-docs/models/deepseek-v4-flash/),
[Token Factory terms](https://amd-aim.github.io/radeon-cloud-docs/api/terms/).
The public shared-key use decision remains separate from this authorized local evaluation.
