# Tarvio portfolio demo preparation

Status: implemented locally; a small authorized Token Factory evaluation is verified.
Deployment-host and public-provider activation gates remain open. No Freestyle resource,
public endpoint, remote push or paid service was activated.
Earlier container source/images: `aadc8f3661145e50613959bf5901c6fd5ba6494f`.
Those images predate the live prompt corrections; rebuild from the intended current
source before rollout. Historical identities: [portfolio evidence](evidence/portfolio.json).
Current live results: [verification note](live-provider-verification.md) and
[machine-readable evidence](evidence/live-token-factory-20261030.json).

## Focused product changes

- Inbox search is authorized on the server across all matching conversations and actual message text. Queries accept 2–120 characters, pages 1–100 rows, a 1.5-second SQL statement deadline and a stable activity-time/UUID cursor through `X-Next-Cursor`. Literal wildcard characters are escaped. A pg_trgm index supports message substring search.
- Titles use the first persisted customer message; previews use the last persisted message. Markdown delimiters are extracted deterministically and text is bounded. No model or invented customer identity is involved. Partial loaded-row counts were removed.
- Knowledge owns assistant activation. `/app/$workspaceId/settings` redirects to Knowledge and the redundant navigation link is gone.
- Public capabilities expose `demo_available`, `ai_mode` and, only for an existing local fixture, optional `customer_entry_key`. Home links the shared customer page beside staff login, with a short explanation of its relationship to the isolated demo. Production omits the permanent fixture entry. Capability failures show retry without invented fallback. The single compact indicator distinguishes fictional data from simulated/live/disabled generation.
- Fictional business fixtures now consistently use Tarvio Cloud. The explicit seed upgrades the known legacy development account/key and adds immutable replacement versions, preserving old transcripts/citations. Production template seeding creates no reusable staff login. Public visitor bootstrap cannot enter the permanent production fixture template; each public demo remains isolated and expiring.
- Technical retry/protocol wording moved out of the product. The entry illustration is visibly and accessibly marked as an illustration. Existing RTL, local fonts, native source sheets and responsive panes remain.

## Provider compatibility and authorization

Official sources checked on 2026-10-30:

- [Token Factory guide](https://amd-aim.github.io/radeon-cloud-docs/guides/token-factory/), linked from the [official console](https://developer.amd.com.cn/radeon/tokenfactory).
- [Chat Completions](https://amd-aim.github.io/radeon-cloud-docs/api/chat-completions/), [model catalog](https://amd-aim.github.io/radeon-cloud-docs/models/overview/), [rate limits](https://amd-aim.github.io/radeon-cloud-docs/api/rate-limits/), [terms](https://amd-aim.github.io/radeon-cloud-docs/api/terms/).

The documented compatible base is `https://developer.amd.com.cn/radeon/api/v1`.
The catalog currently lists text models including `DeepSeek-V4-Flash` and `Qwen3.8-27B`.
On 2026-10-30 the authorized authenticated `/models` check returned 200 and confirmed
`DeepSeek-V4-Flash`. The final six-case local evaluation passed with that model, plus
a real browser customer/source/operator flow. Credentials remain backend-only and ignored.

The adapter uses one first-position `system` message, delimited JSON references treated
as untrusted data, and bounded whole conversation turns. New runs record `answer-v4`;
queued runs with a different prompt version cannot silently execute the changed prompt.
Local E5/pgvector retrieval is unchanged. There is no fake fallback after a live error.
The prompt resolves follow-up questions using history and requests the exact no-answer
marker for insufficient evidence. Citation-only output is rejected before final publication.

SSE parsing validates framing, usage types, completion reason and `[DONE]`; malformed,
truncated and unsupported tool output cannot become final answers. Usage-only frames do
not create gaps in AI text chunk indexes. Connect/read/total timeouts are configurable;
the total provider deadline is cancellable and at most 90 seconds per attempt. Existing
Celery AI soft/hard bounds remain 110/120 seconds, with at most three DB-scheduled attempts.
`Retry-After` seconds or HTTP dates are respected; waits exceeding the configured cap
terminate the run rather than retrying early. Known failed-attempt usage is reconciled;
omitted or ambiguous usage remains conservatively charged.

Token Factory's terms distinguish development/demos from production and restrict
providing endpoint access to third parties, including behind a proxy and without payment.
Public shared-key activation remains unresolved: obtain provider confirmation for the
intended use or select another compatible provider with permitted terms. Production
live admission defaults off through `PUBLIC_LIVE_AI_ENABLED=false`; this does not block
local development or the explicitly simulated public demo.

To evaluate locally after securely configuring the backend and restarting all roles:

```bash
# Backend-only: LLM_PROVIDER=compatible_http, LLM_BASE_URL, LLM_API_KEY,
# LLM_MODEL, LLM_CONTEXT_LIMIT. Do not place a key in frontend variables or reports.
cd apps/backend
uv run --locked --all-extras python -m supportdesk.cli.evaluate_live --allow-live
```

The opt-in evaluator is limited to the local development origin and at most six customer
turns: Persian supported questions, follow-up, unsupported/injection questions and handoff
after the first actual WebSocket AI delta. It retrieves authorized citations, separates
new answers from previous turns and exits unsuccessfully when a case fails. A completed
model that finishes before handoff cannot count as a passed streaming handoff. Human
claim-support review is still required; structural citations do not prove faithfulness.
One real timeout recovered through bounded retry; its unknown cost stayed charged.
Malformed/429/deadline coverage remains controlled HTTP testing, without live overload.

## Shared resource bounds

Defaults are configurable in `deploy/production.env.example`:

| Bound | Default and semantics |
| --- | --- |
| Application input/output | 6,000 conservative UTF-8 byte/framing units + 800 output tokens per attempt; model context only constrains this further |
| Reservation | 3 × 6,800 = 20,400 tokens initially; a model advertising a million-token context does not enlarge it |
| Workspace/provider daily budget | 100,000 / 200,000 tokens, UTC periods; provider ledger shared across every workspace and retained after demo deletion |
| Concurrent/queued AI | One valid running job lease, ten queued/running runs installation-wide; one Celery process initially |
| Public demo creation | Five session creations/minute/IP; 50 demos/day installation-wide; 50 active isolated demo workspaces |
| Upload/ingestion | 20 upload attempts/day globally, 10/hour/IP and workspace, five unfinished ingestion jobs globally, 10 MiB/file |
| Committed artifact storage | 256 MiB across all workspaces; clone/upload admission serialized by a shared PostgreSQL lock |
| Conversation/message admission | 2,000 new conversations/day and 5,000 new messages/day globally, plus existing actor limits; authorized replays precede durable command quotas |
| Expiry/retention | Hourly supervised cleanup, up to 50 expired workspaces per batch, existing transcript/source/outbox policies and 24-hour orphan-file grace |

The provider ledger, workspace ledgers and reservations change in the same transaction.
Unknown external cost survives expiry; only never-started or known-unused reservations
are released. Provider calls may still be repeated after ambiguous failures; billing is
not exactly once. Global upload-attempt caps also bound abandoned files during the orphan
grace interval. Trusted CLI fixture provisioning is an explicit operator operation.

## Complete-stack local package

`deploy/compose.production.yaml` contains gateway, API, dispatcher, worker, PostgreSQL,
Redis and hourly retention, plus one-shot migrate/roles/model/seed/readiness services.
Only the gateway publishes a port. Database, artifact, model-cache and Redis data use
named persistent volumes. Logs rotate at five 10 MiB files per service; configure an
external collector if time-based log retention is required.

Runtime containers receive the restricted database URL, not owner credentials. The
owner-only `runtime_role` command grants data access, removes schema-create/superuser
capabilities and protects the migration-version table. Migrations run before runtime
rollout. The explicit production seed builds only fictional templates, not demo passwords.

```bash
# One-time inputs: copy deploy/production.env.example to private .env.production,
# replace secrets/domain/release values, and keep the file outside Git.
PORTFOLIO_ENV_FILE=.env.production bash scripts/production-start.sh
```

This builds pinned-lockfile images, waits for private services, migrates, provisions the
runtime role/model, seeds fixtures, starts supervised roles, waits for the exact five
fixture hashes and finally starts the gateway. Model weights are provisioned before
serving; requests never download them. Keep the owner URL solely for migrations/roles.

The local verification stack uses a separate Compose project, database, Redis, files,
model volume, private network and loopback port 5182. Its generated secret file and test
sessions remain ignored under `.local/`. It does not truncate development data. A cached
model copy must dereference shared blob links, or include their backing blob directory;
a shallow cache-directory copy is insufficient.

The complete startup script passed locally at the source revision above. All three
image labels match it; API/gateway/PostgreSQL/Redis were healthy and supervised roles
were running. A fresh full HTTP/ingestion/WebSocket smoke and a persisted-message
resume passed after replacing the application images. This is local container proof,
not an actual Freestyle deployment or a public HTTPS test.

## Freestyle handoff

Current official references: [Docker/Compose](https://www.freestyle.sh/docs/guides/run-docker-in-a-sandbox),
[VM lifecycle](https://www.freestyle.sh/docs/vms/lifecycle), [CLI](https://www.freestyle.sh/docs/vms/cli).
Ubuntu VMs include Docker/Compose. Use a persistent VM with sufficient measured CPU,
memory and disk for PostgreSQL plus local E5; do not transfer historical host performance
claims. Explicitly remove idle/run/deletion limits that would suspend workers or delete
persistent data, then inspect the VM's effective policy and plan caps.

No target/account/domain authorization was available. Remaining deployment inputs:

1. Authorized existing Freestyle VM ID/slug and account access, or separate authorization to create a resource.
2. Public HTTPS domain (an available `style.dev` name or a verified custom domain).
3. Actual trusted ingress proxy addresses/CIDRs and confirmation that raw gateway access is not publicly allowed.
4. Private production secrets and the selected source revision; an encrypted backup recipient/destination.
5. A permitted generation provider/public-use decision if live public AI is desired.

After deployment is separately authorized, transfer the source and private configuration
using the documented CLI; do not put secrets in source archives:

```bash
freestyle vm update "$FREESTYLE_VM_ID" --idle-timeout-seconds -1
freestyle vm exec "$FREESTYLE_VM_ID" -- sudo install -d -o ubuntu -g ubuntu /opt/tarvio
freestyle vm scp ./supportdesk-source.tar.gz "$FREESTYLE_VM_ID:/opt/tarvio/source.tar.gz"
# Transfer the private environment through the authorized secret channel separately.
freestyle vm exec "$FREESTYLE_VM_ID" -- bash -lc 'cd /opt/tarvio && tar -xzf source.tar.gz && PORTFOLIO_ENV_FILE=.env.production bash scripts/production-start.sh'
```

Also set `maxRunSeconds`, `maxRunTotalSeconds`, `ttlSeconds` and `autoDeleteSeconds` to
`-1` where the account permits, with the official VM update interface. Check effective
values; storage alone does not keep a paused VM's worker executing.

Set `GATEWAY_BIND_ADDRESS=0.0.0.0` in the VM configuration, since Freestyle ingress must
reach the published gateway rather than a loopback-only listener. Keep PostgreSQL/Redis
unpublished and allow only the intended TLS ingress through the VM firewall. Create the
single-origin domain rule through the official SDK after authorization:

```javascript
await freestyle.tls.rules.create({
  action: "allow",
  domain: publicDomain,
  source: { public: true },
  destination: { vmId, port: 8080 },
});
```

Freestyle supplies domain HTTPS. Set exact `ALLOWED_ORIGINS` and secure cookies. API
Uvicorn forwarding is disabled; the application trusts only the fixed gateway container
address. Caddy accepts forwarding only from explicit `EDGE_TRUSTED_PROXIES`, processes
that chain from the right and replaces the outgoing X-Forwarded-For with its validated
client address. Never trust `0.0.0.0/0` or arbitrary inbound forwarding headers.
The fixed gateway address is outside Docker's dynamic address range; configure subnet,
bridge, dynamic range and gateway together if their defaults conflict with the host.

After routing, verify real HTTPS, cookies, WebSocket reconnect, and two actual unrelated
visitor addresses on that host. The local synthetic trusted-edge test is not host proof.

```bash
curl --fail "https://$PUBLIC_DOMAIN/api/v1/health/ready"
curl --fail "https://$PUBLIC_DOMAIN/api/v1/public/capabilities"
# Then complete the browser workflow and inspect the actual running VM policy/volumes.
```

## Backup, restore and rollback

Keep the previous immutable image tags and take a coordinated backup before migrations.
During an operator-controlled maintenance window:

```bash
PORTFOLIO_ENV_FILE=.env.production BACKUP_AGE_RECIPIENT="$AGE_RECIPIENT" bash scripts/production-backup.sh
```

The script stops writes/retention, dumps PostgreSQL, archives files, records their hash
manifest, optionally encrypts with `age`, and restarts services via a trap. It performs
no implicit off-host transfer. An encrypted off-host destination and tested recipient
are still required. A private local drill can explicitly select
`ALLOW_UNENCRYPTED_LOCAL_BACKUP=1`; this is not an encrypted off-host backup.

Restore into a new database and private file directory/volume, never over the only live
copy. On an isolated PostgreSQL host, create a new `*_test` database, restore with
`pg_restore -U supportdesk_owner --no-owner`, extract `files.tar` into a separate `files/`
directory and run `supportdesk.cli.backup_manifest` with `VERIFY_BACKUP_ROOT` and
`RESTORE_DATABASE_NAME`. It compares database references, byte sizes and SHA-256 values.
Switch traffic only after the restored stack passes readiness and application checks.

The local drill helper performs these steps and refuses to overwrite the live database:

```bash
PORTFOLIO_ENV_FILE=.env.production bash scripts/production-restore-drill.sh "$PRIVATE_BACKUP_DIRECTORY"
```

For an application-only rollback, point the Compose service image tags to the retained
compatible revision and recreate API/dispatcher/worker/gateway while keeping named volumes.
Do not run `down -v` and do not blindly downgrade the schema. Migration 0008 adds columns,
indexes and a ledger, but the previous API's explicit schema check expects 0007; therefore
that old release cannot simply be started against 0008. Either keep a forward-compatible
rollback build with the current schema check or restore the coordinated pre-upgrade backup
into a separate stack and switch traffic. Retain the failed/new database for investigation.

## Verification boundaries

Fresh commands/results, screenshots, failures and recovery are recorded in
[progress](progress.md). Previous release and benchmark manifests remain historical.
Live generation, public TLS/Freestyle host behavior, physical mobile keyboard behavior,
independent human ratings and encrypted off-host restore are not inferred from local tests.
