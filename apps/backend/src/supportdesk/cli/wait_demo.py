"""Bounded readiness check for the real seeded browser-test application."""

import asyncio

import httpx

from supportdesk.cli.wait_knowledge import template_ready
from supportdesk.infrastructure.database import Session


async def wait() -> None:
    async with httpx.AsyncClient(trust_env=False, timeout=2) as client:
        async with asyncio.timeout(150):
            while True:
                try:
                    web = await client.get("http://localhost:5173")
                    api = await client.get("http://localhost:8000/api/v1/health/ready")
                    async with Session() as db:
                        ready = await template_ready(db)
                    if web.status_code == api.status_code == 200 and ready:
                        print("API, UI and five fictional documents are ready")
                        return
                except (httpx.TransportError, OSError):
                    pass
                await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(wait())
