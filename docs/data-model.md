# Data model

Alembic migrations are authoritative; see `apps/backend/migrations/versions/`.
`workspaces` scope actors, conversations, messages, knowledge and durable jobs.
Messages and events use explicit conversation sequence numbers. Composite tenant keys
protect conversation/message/source relationships. Session tokens are stored only as SHA-256 hashes.

A conversation separates lifecycle (`open/resolved`) from controller (`bot/queue/human`).
Only human control has an assignee. A row lock serializes sends and ownership changes.
`state_version` protects control commands; `control_epoch` fences old assistant work.
Command receipts protect lost successful command responses independently of state versions.

Document versions and chunks are immutable once ready. A document's active-version pointer
changes only after indexing commits. Withdrawal removes retrieval access immediately and
preserves historical message content and citation metadata. No user account deactivation
cascades away message history.

Jobs are authoritative in PostgreSQL, with three execution attempts, random lease tokens,
renewals, generation-numbered dispatch outbox records and recovery scans. A final AI message
has a unique run ID. Usage reservations cover all three attempts; unknown external usage
remains charged conservatively until reconciled.
