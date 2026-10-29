"""Explicit fictional development fixtures; never executed on API startup."""

import asyncio
import os

from sqlalchemy import select

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session
from supportdesk.modules.identity.models import StaffUser
from supportdesk.modules.identity.service import passwords
from supportdesk.modules.workspaces.models import Actor, Workspace


async def seed() -> None:
    if get_settings().app_env == "production":
        raise RuntimeError("Development fixtures cannot be seeded in production")
    password_hash = passwords.hash(
        os.environ.get("DEMO_PASSWORD", "Fictional-Demo-Only-2026!")
    )
    async with Session.begin() as db:
        for key, email in [
            ("naran-demo", "admin@naran.invalid"),
            ("other-demo", "admin@other.invalid"),
        ]:
            if await db.scalar(select(Workspace).where(Workspace.public_key == key)):
                continue
            workspace = Workspace(public_key=key, name=f"Fictional {key}")
            user = StaffUser(normalized_email=email, password_hash=password_hash)
            db.add_all([workspace, user])
            await db.flush()
            db.add_all(
                [
                    Actor(
                        workspace_id=workspace.id,
                        kind="staff",
                        user_id=user.id,
                        role="admin",
                        display_name="Fictional administrator",
                    ),
                    Actor(
                        workspace_id=workspace.id,
                        kind="assistant",
                        display_name="Fixture assistant",
                    ),
                ]
            )
    print("Fictional fixtures ready: naran-demo, other-demo")


if __name__ == "__main__":
    asyncio.run(seed())
