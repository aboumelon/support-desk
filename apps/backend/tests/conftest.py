import os
from pathlib import Path

# Test commands must opt into a dedicated database. Never truncate the demo database.
os.environ["APP_ENV"] = "test"
os.environ["STORAGE_ROOT"] = str(
    Path(__file__).resolve().parents[3] / ".local" / "test-files"
)
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:56379/15")
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://supportdesk:local-development-only@127.0.0.1:55432/supportdesk_test",
)

import psycopg  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from supportdesk.infrastructure.database import Session, engine  # noqa: E402
from supportdesk.main import create_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database_test_lock():
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url, autocommit=True) as lock:
        lock.execute("SELECT pg_advisory_lock(hashtext(current_database()), 17)")
        yield


@pytest_asyncio.fixture(autouse=True)
async def clean_database(database_test_lock):
    assert engine.url.database and engine.url.database.endswith("_test")
    async with Session.begin() as db:
        await db.execute(
            text(
                "TRUNCATE sessions, workspace_actors, workspaces, staff_users, "
                "rate_limit_buckets CASCADE"
            )
        )
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    ) as value:
        yield value
