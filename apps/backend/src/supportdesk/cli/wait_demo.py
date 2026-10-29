"""Bounded readiness check for the real seeded browser-test application."""

import asyncio

import httpx
from sqlalchemy import func, select

from supportdesk.infrastructure.database import Session
from supportdesk.modules.knowledge.models import Document
from supportdesk.modules.workspaces.models import Workspace


async def wait() -> None:
    async with httpx.AsyncClient(trust_env=False, timeout=2) as client:
        async with asyncio.timeout(150):
            while True:
                try:
                    web = await client.get("http://localhost:5173")
                    api = await client.get("http://localhost:8000/api/v1/health/ready")
                    async with Session() as db:
                        ready = await db.scalar(
                            select(func.count())
                            .select_from(Document)
                            .join(Workspace, Workspace.id == Document.workspace_id)
                            .where(
                                Workspace.public_key == "naran-demo",
                                Document.active_version_id.is_not(None),
                                Document.withdrawn_at.is_(None),
                            )
                        )
                    if web.status_code == api.status_code == 200 and ready == 5:
                        print("API, UI and five fictional documents are ready")
                        return
                except (httpx.TransportError, OSError):
                    pass
                await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(wait())
