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

Inside the repository on the VM, replace these two values:

```bash
export PUBLIC_DOMAIN=your-unused-name.style.dev
export EDGE_TRUSTED_PROXIES='REPLACE_WITH_ACTUAL_INGRESS_IP_OR_CIDR'
```

The following generates distinct strong owner/runtime/session secrets, correct database
URLs and a 0600 `.env.production`. It refuses to overwrite an existing file, preserving
database passwords on later rollouts. It starts with explicitly simulated AI and does
not read or copy your local live key.

```python
import ipaddress
import json
import os
from pathlib import Path
import secrets
import subprocess
from urllib.parse import urlsplit

domain = os.environ["PUBLIC_DOMAIN"].strip().lower()
url = urlsplit("https://" + domain)
if url.netloc != domain or url.hostname != domain or "." not in domain:
    raise ValueError("Use a public hostname without a scheme, path or port")
if any(c.isspace() for c in domain) or url.port is not None:
    raise ValueError("Invalid hostname")
proxies = os.environ["EDGE_TRUSTED_PROXIES"].split()
if not proxies or any(ipaddress.ip_network(p, strict=False).prefixlen == 0 for p in proxies):
    raise ValueError("Trust only actual specific ingress addresses or CIDRs")
release = os.environ.get("RELEASE_ID") or subprocess.check_output(
    ["git", "rev-parse", "HEAD"], text=True
).strip()
owner, runtime = secrets.token_hex(32), secrets.token_hex(32)
values = {
    "RELEASE_ID": release,
    "PUBLIC_BASE_URL": "https://" + domain,
    "ALLOWED_ORIGINS": json.dumps(["https://" + domain]),
    "SESSION_SECRET": secrets.token_hex(32),
    "POSTGRES_OWNER_PASSWORD": owner,
    "MIGRATION_DATABASE_URL": f"postgresql+psycopg://supportdesk_owner:{owner}@postgres:5432/supportdesk",
    "RUNTIME_DATABASE_URL": f"postgresql+psycopg://supportdesk_runtime:{runtime}@postgres:5432/supportdesk",
    "GATEWAY_BIND_ADDRESS": "0.0.0.0",
    "EDGE_TRUSTED_PROXIES": " ".join(proxies),
}
lines = Path("deploy/production.env.example").read_text().splitlines()
content = "\n".join(
    f"{line.split('=', 1)[0]}={values[line.split('=', 1)[0]]}"
    if "=" in line and not line.startswith("#") and line.split("=", 1)[0] in values
    else line for line in lines
) + "\n"
fd = os.open(".env.production", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as output:
    output.write(content)
print("Created private .env.production; secret values were not printed.")
```

Run that block with Python 3, for example by saving it in `/tmp/prepare-tarvio.py`
and running `python3 /tmp/prepare-tarvio.py` from the repository root. Keep
`COMPOSE_PROJECT_NAME=supportdesk-production` stable so later releases reuse the same volumes.

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
