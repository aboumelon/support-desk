"""Create disposable isolated benchmark sessions; never runs on the demo database."""

import asyncio
import json
import secrets
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import text

from supportdesk.config import project_root
from supportdesk.infrastructure.database import Session, engine, now
from supportdesk.modules.conversations.service import create_conversation
from supportdesk.modules.identity.models import LoginSession
from supportdesk.modules.identity.service import digest
from supportdesk.modules.workspaces.models import Actor, Workspace


async def prepare() -> None:
    if not engine.url.database or not engine.url.database.endswith("_benchmark"):
        raise RuntimeError("Dedicated *_benchmark database required")
    result = []
    async with Session.begin() as db:
        await db.execute(
            text(
                "TRUNCATE workspaces, staff_users, sessions, rate_limit_buckets CASCADE"
            )
        )
        workspace = Workspace(
            id=uuid4(),
            public_key="isolated-load-test",
            name="Disposable benchmark",
            ai_enabled=False,
        )
        db.add(workspace)
        await db.flush()
        for _ in range(200):
            actor = Actor(
                id=uuid4(),
                workspace_id=workspace.id,
                kind="visitor",
                display_name="Fictional load client",
            )
            db.add(actor)
            await db.flush()
            conversation = await create_conversation(db, actor, str(uuid4()))
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.add(
                LoginSession(
                    token_hash=digest(token),
                    visitor_actor_id=actor.id,
                    csrf_secret=csrf,
                    expires_at=now() + timedelta(hours=1),
                    last_seen_at=now(),
                )
            )
            result.append(
                {"conversation": str(conversation.id), "token": token, "csrf": csrf}
            )
    path = project_root() / ".local" / "benchmark-sessions.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result))
    path.chmod(0o600)
    print("Prepared 200 isolated clients; credentials saved under ignored .local")


if __name__ == "__main__":
    asyncio.run(prepare())
