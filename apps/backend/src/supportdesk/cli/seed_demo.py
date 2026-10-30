"""Explicit fictional development fixtures; never executed on API startup."""

import asyncio
import os

from sqlalchemy import select

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session
from supportdesk.modules.identity.models import StaffUser
from supportdesk.modules.identity.service import passwords
from supportdesk.modules.workspaces.models import Actor, Workspace


async def seed(portfolio_template: bool = False) -> None:
    if get_settings().app_env == "production" and not portfolio_template:
        raise RuntimeError("Development fixtures cannot be seeded in production")
    password_hash = passwords.hash(
        os.environ.get("DEMO_PASSWORD", "Fictional-Demo-Only-2026!")
    )
    async with Session.begin() as db:
        # Upgrade only known fictional development fixtures; preserve their history.
        legacy = await db.scalar(
            select(Workspace).where(Workspace.public_key == "naran-demo")
        )
        if legacy:
            legacy.public_key, legacy.name, legacy.fictional_data = (
                "tarvio-demo",
                "Tarvio Cloud (fictional)",
                True,
            )
        legacy_user = await db.scalar(
            select(StaffUser).where(StaffUser.normalized_email == "admin@naran.invalid")
        )
        if legacy_user:
            legacy_user.normalized_email = "admin@tarvio.invalid"
        for key, email in [
            ("tarvio-demo", "admin@tarvio.invalid"),
            ("other-demo", "admin@other.invalid"),
        ]:
            if await db.scalar(select(Workspace).where(Workspace.public_key == key)):
                continue
            workspace = Workspace(
                public_key=key,
                name="Tarvio Cloud (fictional)"
                if key == "tarvio-demo"
                else "Other fictional workspace",
                fictional_data=True,
            )
            if portfolio_template:
                db.add(workspace)
                await db.flush()
                db.add(
                    Actor(
                        workspace_id=workspace.id,
                        kind="assistant",
                        display_name="Tarvio assistant",
                    )
                )
                continue
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
    print("Fictional fixtures ready: tarvio-demo, other-demo")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--portfolio-template",
        action="store_true",
        help="Create explicitly fictional templates without reusable staff credentials",
    )
    asyncio.run(seed(parser.parse_args().portfolio_template))
