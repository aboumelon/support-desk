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

Admin uploads accept multipart `title` and `file` fields, return 202 and durable job IDs.
Activate the assistant using the workspace `/assistant` PUT after at least one document
is ready. The current live HTTP adapter uses a configured Chat Completions-compatible
endpoint; it has not been verified against a live provider.
