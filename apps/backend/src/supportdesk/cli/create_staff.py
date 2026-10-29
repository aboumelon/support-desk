"""Create an explicit workspace administrator using an interactive password prompt."""

import argparse
import asyncio
import getpass

from sqlalchemy import select

from supportdesk.infrastructure.database import Session
from supportdesk.modules.identity.models import StaffUser
from supportdesk.modules.identity.service import passwords
from supportdesk.modules.workspaces.models import Actor, Workspace


async def create(email: str, key: str, name: str, password: str) -> None:
    if len(password) < 12:
        raise ValueError("Password must have at least 12 characters")
    hashed = passwords.hash(password)
    async with Session.begin() as db:
        if await db.scalar(
            select(StaffUser.id).where(StaffUser.normalized_email == email.casefold())
        ):
            raise ValueError(
                "Staff identity already exists; use the membership workflow"
            )
        workspace = await db.scalar(
            select(Workspace).where(Workspace.public_key == key)
        )
        if workspace is None:
            workspace = Workspace(public_key=key, name=name)
            db.add(workspace)
            await db.flush()
            db.add(
                Actor(
                    workspace_id=workspace.id,
                    kind="assistant",
                    display_name="Assistant",
                )
            )
        user = StaffUser(
            normalized_email=email.strip().casefold(), password_hash=hashed
        )
        db.add(user)
        await db.flush()
        db.add(
            Actor(
                workspace_id=workspace.id,
                kind="staff",
                user_id=user.id,
                role="admin",
                display_name=name,
            )
        )
    print("Administrator created")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--workspace-key", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    asyncio.run(
        create(
            args.email,
            args.workspace_key,
            args.name,
            getpass.getpass("New administrator password: "),
        )
    )
