# Evaluation evidence

The 40 cases in `evals/rag/cases.jsonl` contain 20 answerable questions, 10 missing-knowledge
questions, five workspace isolation cases and five instruction-injection cases. Five
explicitly fictional documents and a pinned E5 revision make retrieval reproducible.
Run `uv run --all-extras python -m supportdesk.cli.evaluate_rag` in `apps/backend`.

`evidence/rag-baseline-v1.json` preserves the first measurement: recall@5 1.0,
correct handoff 0.625, zero source-isolation failures, structurally valid source labels.
Recall@5 on only five source documents is a weak quality signal; top-rank performance
and a larger corpus are required before generalizing.

The fake provider was then narrowed to explicit fixture topics and no-answer scripts.
`evidence/rag-fixture.json` measures deterministic fixture coverage after that change.
The cases were inspected during implementation, so the original held-out labels do not
represent an untouched blind evaluation. Create fresh blind cases before making a model
quality claim. Neither report establishes live-model accuracy. Human claim-support
ratings are explicitly uncollected; no paid provider was called.

The PostgreSQL fake-provider tests check handoff/new-turn/withdrawal races, invalid
citations, budgets, unknown usage and bounded timeout/rate-limit/drop failures.
The real Redis/Celery test checks actual ingestion and duplicate dispatch. The two-API
test checks live delivery, a lost final notification and replay after reconnect.

The k6 benchmark uses 200 isolated sessions, two API replicas, a dedicated database and
Redis broker namespace, ten minutes of normal traffic, a short burst and reconnect wave.
See the measured benchmark evidence once the run finishes. Development-host measurements
are not deployment capacity guarantees.
