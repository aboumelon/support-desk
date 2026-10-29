# Implementation plan

Authority: [original design](../supportdesk-system-design-v1.md). Root: `/home/armin/projects/support-desk`.

| Milestone | Deliverables | Acceptance checks |
| --- | --- | --- |
| M0 | Locked Python/Node monorepo, validated configuration, Alembic, tenant keys, separate opaque sessions, CSRF/origin protection, fixtures, Persian UI, generated contracts, CI | Real PostgreSQL migration/seed; staff/customer isolation; expiry, CSRF and cross-workspace tests; lint, types, production build |
| M1 | Transactional messages/events/outbox, command receipts, snapshots, history, state model | Concurrent identical/conflicting retries and ordering; restart/refresh persistence; tenant foreign keys |
| M2 | Leased dispatcher, realtime replay/watermarks, operator inbox and ownership | Two API instances; lost final notification; competing claims; reconnect and receipts without feedback |
| M3 | Private uploads, immutable versions, bounded extraction, pinned E5 embeddings, ready-only retrieval | Replacement/withdrawal races; parser limits; tenant/source isolation |
| M4 | Deterministic and configurable live provider, provisional streams, citations, budgets, durable jobs and publication fences | Slow/failing provider; handoff/new-turn/lease/source races; bounded recovery; explicit unverified live checks |
| M5 | 40-case evaluation, measured load/recovery, deployment/restore instructions, release evidence | Reproducible reports; 200 connections and specified load; restore drill; browser flows; no unsubstantiated guarantees |

Work in dependency order. A milestone is complete only after its acceptance gates pass. Network calls must remain outside transactions. Preserve the original design. Record deviations in ADRs. No remote publishing or paid service activation.

## Current checkpoint

M0–M4 local acceptance gates passed against PostgreSQL/Redis/Celery and the explicit
fake provider. M5 local browser, healthy/recovery load, image and DB/file restore
evidence is recorded. Independent human/blind quality evaluation, an off-host
encrypted restore and live-provider verification remain unverified. Consult
`progress.md` and `evidence/release.json` before making a release claim.
