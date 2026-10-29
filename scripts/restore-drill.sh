#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
stamp=$(date -u +%Y%m%d%H%M%S)
restore_database="supportdesk_drill_${stamp}_test"
drill_directory="$PWD/.local/restore-$stamp"
mkdir -p "$drill_directory/files"
started=$(date +%s)
# Immutable files may be copied after the DB snapshot while purge jobs are paused.
docker compose -f compose.yaml -f compose.dev.yaml exec -T postgres pg_dump -U supportdesk -Fc supportdesk >"$drill_directory/database.dump"
cp -a .local/files/. "$drill_directory/files/"
docker compose -f compose.yaml -f compose.dev.yaml exec -T postgres createdb -U supportdesk "$restore_database"
docker compose -f compose.yaml -f compose.dev.yaml exec -T postgres pg_restore -U supportdesk -d "$restore_database" <"$drill_directory/database.dump"
RESTORE_DATABASE="$restore_database" RESTORE_FILES="$drill_directory/files" RESTORE_STARTED="$started" apps/backend/.venv/bin/python - <<'PY'
import hashlib
import json
import os
import time
from pathlib import Path

import psycopg

database = os.environ['RESTORE_DATABASE']
assert database.startswith('supportdesk_drill_') and database.endswith('_test')
root = Path(os.environ['RESTORE_FILES']).resolve()
with psycopg.connect(f'postgresql://supportdesk:local-development-only@127.0.0.1:55432/{database}') as db:
    artifacts = db.execute("SELECT storage_key, sha256, bytes FROM artifacts a WHERE state='ready' AND EXISTS (SELECT 1 FROM document_versions v WHERE v.artifact_id=a.id)").fetchall()
for key, expected, size in artifacts:
    path = (root / key).resolve()
    assert path.parent == root, 'Artifact key escaped the private storage root'
    content = path.read_bytes()
    assert len(content) == size and hashlib.sha256(content).hexdigest() == expected
report = {'database': database, 'restored_artifacts': len(artifacts), 'hashes_verified': len(artifacts), 'local_duration_seconds': round(time.time()-int(os.environ['RESTORE_STARTED']), 2), 'off_host_encrypted_restore': 'not performed', 'command': 'bash scripts/restore-drill.sh', 'purge_policy': 'Do not run purges while taking the DB/file snapshot'}
Path('docs/evidence/restore.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
PY
