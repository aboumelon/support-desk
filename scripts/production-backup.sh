#!/usr/bin/env bash
# Run during an operator-controlled maintenance window. No external transfer is implicit.
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
compose=(docker compose --env-file "${PORTFOLIO_ENV_FILE:-.env.production}" -f deploy/compose.production.yaml)
backup_root="${BACKUP_ROOT:-.local/backups}"
mkdir -p "$backup_root"
backup_directory=$(mktemp -d "$backup_root/portfolio-$(date -u +%Y%m%dT%H%M%SZ)-XXXX")
if [ -z "${BACKUP_AGE_RECIPIENT:-}" ] && [ "${ALLOW_UNENCRYPTED_LOCAL_BACKUP:-}" != 1 ]; then
  echo 'Set BACKUP_AGE_RECIPIENT, or explicitly select a private unencrypted local restore drill.' >&2
  exit 1
fi
if [ -n "${BACKUP_AGE_RECIPIENT:-}" ]; then command -v age >/dev/null; fi
"${compose[@]}" stop gateway api worker dispatcher retention
trap '"${compose[@]}" up -d api dispatcher worker retention gateway >/dev/null' EXIT
"${compose[@]}" exec -T postgres pg_dump -U supportdesk_owner -Fc supportdesk >"$backup_directory/database.dump"
"${compose[@]}" run --rm --no-deps --entrypoint tar api -C /var/lib/supportdesk/files -cf - . >"$backup_directory/files.tar"
"${compose[@]}" run --rm --no-deps --entrypoint python api -m supportdesk.cli.backup_manifest >"$backup_directory/manifest.json"
if [ -n "${BACKUP_AGE_RECIPIENT:-}" ]; then
  tar -C "$backup_directory" -cf - database.dump files.tar manifest.json | age -r "$BACKUP_AGE_RECIPIENT" -o "$backup_directory.tar.age"
  rm "$backup_directory/database.dump" "$backup_directory/files.tar" "$backup_directory/manifest.json"
  rmdir "$backup_directory"
  printf 'Encrypted backup: %s.tar.age\n' "$backup_directory"
else
  printf 'Private local drill backup: %s\n' "$backup_directory"
fi
