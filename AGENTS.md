# SupportDesk contributor instructions

Use the repository root directly; do not nest another supportdesk directory.
Read `supportdesk-system-design-v1.md` and `docs/progress.md` before changing behavior.
Source code, identifiers, comments and technical documentation are English. Product copy
is centralized in `apps/web/src/locales/fa.json` and the interface supports Persian RTL.

Use uv with the backend lockfile and pnpm with the workspace lockfile. Do not hand-edit
generated API/realtime contracts. Run `pnpm contracts:check` after backend schema changes.
Use PostgreSQL for concurrency and tenant-boundary tests; SQLite is not acceptable evidence.
Keep external provider calls and inference outside DB transactions. Preserve message/event/
outbox atomicity and epoch/lease/source fences. Do not silently fall back from live to fake AI.

Verification commands are documented in README and the runbook. Keep failed/unavailable
checks and unfinished release gates in progress.md. Never claim a performance target has
passed without measured evidence. Keep local credentials and test-session fixtures ignored.
Do not push, deploy publicly or activate paid services without a separate user request.
