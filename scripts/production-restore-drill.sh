#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
backup_directory=$(realpath "${1:?Pass the private local backup directory}")
for name in database.dump files.tar manifest.json; do test -s "$backup_directory/$name"; done
compose=(docker compose --env-file "${PORTFOLIO_ENV_FILE:-.env.production}" -f deploy/compose.production.yaml)
restore_database="portfolio_restore_$(date -u +%Y%m%d%H%M%S)_${RANDOM}_test"
restore_directory=$(mktemp -d "$PWD/.local/portfolio-restore-XXXX")
mkdir "$restore_directory/files"
cp "$backup_directory/manifest.json" "$restore_directory/manifest.json"
printf 'CREATE DATABASE "%s";\n' "$restore_database" | "${compose[@]}" exec -T postgres psql -U supportdesk_owner -d supportdesk -v ON_ERROR_STOP=1
"${compose[@]}" exec -T postgres pg_restore -U supportdesk_owner --no-owner -d "$restore_database" <"$backup_directory/database.dump"
"${compose[@]}" run --rm --no-deps --user 0 --entrypoint python -v "$backup_directory:/backup:ro" -v "$restore_directory:/restore" api -c 'import tarfile; tarfile.open("/backup/files.tar").extractall("/restore/files",filter="data")'
"${compose[@]}" run --rm --no-deps --user 0 --entrypoint python -v "$restore_directory:/restore:ro" -e VERIFY_BACKUP_ROOT=/restore -e "RESTORE_DATABASE_NAME=$restore_database" api -m supportdesk.cli.backup_manifest
printf 'Restore drill preserved at %s; database %s. Original data was not overwritten.\n' "$restore_directory" "$restore_database"
