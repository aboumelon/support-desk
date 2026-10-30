"""Private backup manifest; invoke with output redirected to a protected file."""

import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from supportdesk.config import get_settings
from supportdesk.main import create_app
from supportdesk.modules.knowledge.models import Artifact

create_app()


def main() -> None:
    settings = get_settings()
    verify = os.environ.get("VERIFY_BACKUP_ROOT")
    url = settings.database_url
    if verify:
        from sqlalchemy.engine import make_url

        name = os.environ["RESTORE_DATABASE_NAME"]
        if not name.endswith("_test"):
            raise RuntimeError("Restore verification requires a new test database")
        url = make_url(url).set(database=name).render_as_string(hide_password=False)
    with Session(create_engine(url, hide_parameters=True)) as db:
        rows = list(db.scalars(select(Artifact).where(Artifact.state == "ready")))
        manifest = {
            item.storage_key: {"sha256": item.sha256, "bytes": item.bytes}
            for item in rows
        }
    if verify:
        root = Path(verify)
        expected = json.loads((root / "manifest.json").read_text())
        if manifest != expected:
            raise RuntimeError("Restored database does not match the artifact manifest")
        for key, value in expected.items():
            if Path(key).name != key:
                raise RuntimeError("Invalid manifest storage key")
            path = root / "files" / key
            if (
                path.stat().st_size != value["bytes"]
                or hashlib.sha256(path.read_bytes()).hexdigest() != value["sha256"]
            ):
                raise RuntimeError("Restored artifact hash mismatch")
        print(json.dumps({"verified_artifacts": len(expected), "database": name}))
    else:
        print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
