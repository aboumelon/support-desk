# Deploy Tarvio on Freestyle

Repository: [aboumelon/support-desk](https://github.com/aboumelon/support-desk), branch `main`.
Official references were checked on 2026-10-30. These are operator instructions;
no Freestyle VM, domain, paid plan or public provider was activated by preparing them.

## 1. Create a persistent Ubuntu VM

On your own computer, install the official CLI and sign in:

```bash
npm install -g freestyle@0.2.21
freestyle login
freestyle whoami
freestyle vm create --snapshot-id freestyle/ubuntu --slug support-desk --no-ssh
freestyle vm update support-desk --idle-timeout-seconds -1 --automatic-restart
freestyle vm get support-desk
```

If Node cannot reach the dashboard directly but your HTTP proxy works, enable
`NODE_USE_ENV_PROXY=1` in that terminal before logging in. Confirm `freestyle whoami`
before creating a VM. A partially completed login can leave a refresh token without
cached teams; `NODE_USE_ENV_PROXY=1 freestyle team list` can complete that cache refresh.
The CLI's `--proxy` flag selects an API base URL, not an HTTP CONNECT proxy.

The documented Ubuntu default is 4 vCPU / 8 GiB / 32 GB and includes Docker/Compose.
It is a starting shape, not a capacity measurement for this application. On Free,
200 vCPU-hours and 400 GiB-hours permit approximately 50 hours/month at that shape;
exhaustion pauses VMs. Check the account's plan and effective lifecycle policy before
relying on continuous availability. No paid upgrade is implicit in these commands.

Inspect `idleTimeoutSeconds`, `maxRunSeconds`, `maxRunTotalSeconds`, `ttlSeconds` and
`autoDeleteSeconds`. Remove unwanted runtime/deletion deadlines using the documented
VM update API, and inspect effective values afterward; plan limits can still apply.
The CLI above exposes idle timeout and automatic restart, not every policy field.
With an authorized private `FREESTYLE_API_KEY` and SDK `freestyle@0.2.21` in a separate
local operations directory, the equivalent full policy update is:

```javascript
import { Freestyle } from "freestyle";
const vm = new Freestyle().vms.ref("support-desk");
await vm.update({
  idleTimeoutSeconds: -1,
  maxRunSeconds: -1,
  maxRunTotalSeconds: -1,
  ttlSeconds: -1,
  autoDeleteSeconds: -1,
  automaticRestart: true,
});
console.log(await vm.data());
```

## 2. Get the repository inside the VM

```bash
freestyle vm ssh support-desk
```

In the VM terminal:

```bash
git clone https://github.com/aboumelon/support-desk.git
cd support-desk
git checkout main
docker --version
docker compose version
```

For a private repository, configure a read-only GitHub deploy key in the VM and use
the SSH clone URL. Do not copy a personal SSH private key into the VM. Alternatively,
from your existing local checkout, transfer only committed source through Freestyle:

```bash
git archive --format=tar.gz --output=/tmp/supportdesk-source.tar.gz HEAD
freestyle vm scp /tmp/supportdesk-source.tar.gz support-desk:/tmp/supportdesk-source.tar.gz
freestyle vm exec support-desk -- bash -lc 'mkdir -p ~/support-desk && tar -xzf /tmp/supportdesk-source.tar.gz -C ~/support-desk'
```

An archive has no `.git`; set `RELEASE_ID` to its source commit before the next step.
No local `.env`, test sessions, dependencies, model weights or database volume is transferred.

## 3. Create private production configuration

Choose an unused `style.dev` hostname, or use a verified custom domain. The hostname
below is a placeholder, not a claimed domain. Obtain the actual ingress proxy IP/CIDR
from the deployment network/platform before trusting forwarded visitor addresses.
The public documentation does not specify a universal trusted edge CIDR; do not guess
one or trust `0.0.0.0/0`. Also keep direct raw gateway ingress closed in the VM firewall;
a TLS rule alone does not deny other access.

Inside the repository on the VM, update an older clone and run the setup helper:

```bash
git pull --ff-only
python3 scripts/prepare-production-env.py --domain your-unused-name.style.dev
```

Replace the hostname with your chosen public hostname. This only writes private
configuration; it does not reserve a domain, publish a route or contact a cloud API.
The helper generates separate owner/runtime/session secrets, matching database URLs,
secure cookies, the exact HTTPS Origin and the current release revision. It writes
`.env.production` with mode 0600 and refuses to overwrite an existing file. No developer
`.env` or live key is copied; initial AI is explicitly simulated.

Without `--trusted-proxy`, it preserves conservative loopback-only proxy trust for
initial private bootstrap. Once the actual ingress address is verified, set
`EDGE_TRUSTED_PROXIES` in the private file before public routing. If already known, pass
`--trusted-proxy IP/CIDR` to the helper (repeat for multiple verified proxies). A global
`0.0.0.0/0` or `::/0` is rejected. Do not guess proxy ranges merely to make a check pass.

| Setting | Purpose | First deployment |
| --- | --- | --- |
| `PUBLIC_BASE_URL`, `ALLOWED_ORIGINS` | Expected public HTTPS address and allowed browser Origin | Derived from `--domain` |
| `SESSION_SECRET` | Private application security secret | Generated automatically |
| `POSTGRES_OWNER_PASSWORD`, `MIGRATION_DATABASE_URL` | Database initialization and migration-owner access | Generated with matching credentials |
| `RUNTIME_DATABASE_URL` | Restricted account used by API/worker/dispatcher | Generated separately from the owner |
| `RELEASE_ID` | Image revision for this release | Current Git commit; archives require `--release-id` |
| `COMPOSE_PROJECT_NAME` | Stable namespace for containers and persistent volumes | Keep `supportdesk-production` across updates |
| `GATEWAY_BIND_ADDRESS`, `GATEWAY_PORT` | HTTP listener reached by the Freestyle edge | `0.0.0.0`, port `8080` |
| `EDGE_TRUSTED_PROXIES` | Verified proxy addresses whose forwarding headers may be trusted | Conservative private bootstrap, then actual edge addresses |
| `DEMO_MODE` | Allow isolated expiring public demos | `true` |
| `LLM_PROVIDER` | Explicit simulated or compatible live generation | `fake` initially |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_CONTEXT_LIMIT` | Backend-only live provider configuration | Configure only when live use is permitted |
| `PUBLIC_LIVE_AI_ENABLED` | Separate production live-admission gate | `false` initially |
| AI/demo/upload/storage limits | Installation-wide and per-workspace resource bounds | Keep defaults for the initial setup |

Later updates reuse the existing file. Do not delete/regenerate it to change the image
revision or proxy settings; edit those values while preserving database secrets and the
Compose project name. The secret values need not be pasted into chats or logs.

## 4. Start the entire stack

Inside the VM repository:

```bash
PORTFOLIO_ENV_FILE=.env.production bash scripts/production-start.sh
docker compose --env-file .env.production -f deploy/compose.production.yaml ps
curl --fail http://127.0.0.1:8080/api/v1/health/ready
```

The startup script builds frontend/API/worker images using the existing lockfiles,
starts private PostgreSQL/Redis, applies migrations, provisions restricted DB roles,
downloads the pinned E5 model once, seeds fictional templates, starts the supervised
API/dispatcher/worker/hourly retention, waits for five current document hashes, then
starts Caddy. Model provisioning needs outbound access to Hugging Face; image builds
need the public package/image registries. Only the gateway publishes port 8080.

## 5. Route HTTPS to port 8080

Back on your own computer, using the same hostname as `.env.production`:

```bash
freestyle tls create --domain your-unused-name.style.dev --from public --to vm=support-desk,port=8080
freestyle tls list --vm support-desk
curl --fail https://your-unused-name.style.dev/api/v1/health/ready
curl --fail https://your-unused-name.style.dev/api/v1/public/capabilities
```

Freestyle terminates HTTPS and manages the certificate; Caddy receives HTTP on 8080.
Do not publish PostgreSQL/Redis, the metrics endpoint or Caddy's admin port. Verify the
real trusted ingress chain and independent session-creation buckets from two visitor
addresses. Complete a browser demo including sources, WebSocket reconnect and human
handoff over HTTPS. Inspect secure cookies and confirm the VM stays running without
browser traffic. These host checks have not been performed by the local verification.

## 6. Accounts and live generation

Production seeds contain no reusable `admin@tarvio.invalid` password. The permanent
local customer-entry link is hidden; public visitors use isolated expiring demos with
their paired staff/customer views. This prevents unrelated public visitors from sharing
one inbox. To create a private real workspace/administrator, run interactively in the VM:

```bash
docker compose --env-file .env.production -f deploy/compose.production.yaml run --rm --no-deps api python -m supportdesk.cli.create_staff --email YOUR_EMAIL --workspace-key YOUR_PUBLIC_KEY --name YOUR_WORKSPACE_NAME
```

Enter a new password at the private prompt. That workspace's customer URL is
`https://YOUR_DOMAIN/chat/YOUR_PUBLIC_KEY`; its knowledge is managed through staff login.
This does not enable the local shared fixture link or a globally privileged demo account.

For live generation, edit only the VM's private `.env.production`: configure the
compatible provider's backend fields and, only if public use is permitted, set
`PUBLIC_LIVE_AI_ENABLED=true`. Recreate API/dispatcher/worker/retention with the same
Compose file. Token Factory's local tests passed, but permission for a public shared-key
demo remains unresolved. Keep the explicit simulated provider or choose a permitted
alternative until that decision is resolved. A failed live call never changes provider.

## 7. Updates and data recovery

Take a coordinated encrypted backup before changing schema/images:

```bash
PORTFOLIO_ENV_FILE=.env.production BACKUP_AGE_RECIPIENT=YOUR_AGE_RECIPIENT bash scripts/production-backup.sh
```

Install `age` on the VM first if needed, and copy the encrypted result to your chosen
off-host destination. That destination and a timed host restore remain operator inputs.
Then fetch/review the release, update only `RELEASE_ID` in the existing private env file,
and rerun `production-start.sh`. Do not regenerate existing database secrets, change
the Compose project name or use `docker compose down -v` during updates. Preserve named
volumes and the previous compatible image tags. See [backup/restore and schema-aware
rollback](portfolio-release.md#backup-restore-and-rollback) for the coordinated procedure.

## References

- [Official CLI](https://www.freestyle.sh/docs/cli) and [VM CLI](https://www.freestyle.sh/docs/vms/cli)
- [Ubuntu snapshots](https://www.freestyle.sh/docs/vms/base-snapshots) and [Docker/Compose](https://www.freestyle.sh/docs/guides/run-docker-in-a-sandbox)
- [Domains CLI](https://www.freestyle.sh/docs/vms/domains-cli) and [TLS ingress](https://www.freestyle.sh/docs/vms/network/tls-inbound)
- [VM lifecycle](https://www.freestyle.sh/docs/vms/lifecycle) and [current plan allowances](https://www.freestyle.sh/docs/vms/pricing-and-limits)
- [Token Factory terms](https://amd-aim.github.io/radeon-cloud-docs/api/terms/)
