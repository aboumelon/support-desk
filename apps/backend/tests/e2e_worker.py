"""Explicit test-only Celery entrypoint; not included in production images/wheels."""

import os
from pathlib import Path

from supportdesk.workers.celery_app import app
from tests.e2e_provider import install

install(Path(os.environ["E2E_BARRIER_DIR"]))
assert app
