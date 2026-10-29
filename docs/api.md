# API

Backend-owned contract: [`../contracts/openapi.json`](../contracts/openapi.json).
Regenerate with `pnpm contracts:generate`; verify with `pnpm contracts:check`.

Separate `/customer` and `/staff/workspaces/{workspace_id}` audiences share conversation services.
Bootstrap a visitor using `/public/workspaces/{public_key}/visitor-sessions`, or use
`/public/demo` to obtain an isolated 24-hour fictional workspace and both audiences.
Use the corresponding bootstrap's CSRF token in `X-CSRF-Token` for mutations and an
exact allowed Origin. Staff login rotates its opaque session; logout revokes it.

Create/control/upload requests use `Idempotency-Key`. Send messages with a persistent
UUID `client_message_id`; a new commit returns 201, replay 200, conflicting text 409.
Snapshots contain state, 50 recent messages, an event cursor, read cursors and the
latest assistant run. History uses base64-encoded sequence cursors; replay pages hold
at most 100 events. The server resolves the author; body-supplied actor IDs are ignored.

New conversation control event payloads include `action`, `actor_id`, and `actor_kind`
alongside the canonical controller/status/assignment fields. Older events remain valid
without these additive fields. The timeline uses persisted transitions for legacy labels.
An event cursor outside the retained range returns 409 `RESET_REQUIRED` with
`details.oldest_available_seq` (null if all events expired) and `details.event_cursor`.
After authorization, a history viewer may resume at `oldest_available_seq - 1` and must
show that older event history is unavailable. This does not reconstruct expired history.

Admin uploads accept multipart `title` and `file` fields, return 202 and durable job IDs.
Activate the assistant using the workspace `/assistant` PUT after at least one document
is ready. The current live HTTP adapter uses a configured Chat Completions-compatible
endpoint; it has not been verified against a live provider.
