import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from fastapi import Request, Response
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.api.errors import Problem
from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session, now
from supportdesk.modules.identity.models import LoginSession, StaffUser
from supportdesk.modules.identity.schemas import Membership, SessionView
from supportdesk.modules.workspaces.models import Actor, RateLimitBucket, Workspace

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash("not-a-real-account-password")


@dataclass
class Principal:
    session: LoginSession
    audience: str
    user: StaffUser | None = None
    actor: Actor | None = None


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def check_origin(request: Request) -> None:
    if request.headers.get("origin") not in get_settings().allowed_origins:
        raise Problem(403, "ORIGIN_REJECTED")


async def rate_limit(
    action: str,
    identity: str,
    limit: int,
    seconds: int = 60,
    db: AsyncSession | None = None,
) -> None:
    bucket_hash = hmac.new(
        get_settings().session_secret.encode(), identity.encode(), hashlib.sha256
    ).hexdigest()
    stamp = now()
    statement = insert(RateLimitBucket).values(
        bucket_hash=bucket_hash,
        action=action,
        window_start=int(stamp.timestamp()) // seconds,
        count=1,
        expires_at=stamp + timedelta(seconds=seconds * 2),
    )
    upsert = statement.on_conflict_do_update(
        index_elements=["bucket_hash", "action", "window_start"],
        set_={"count": RateLimitBucket.count + 1},
        where=RateLimitBucket.count < limit,
    ).returning(RateLimitBucket.count)
    if db is None:
        async with Session.begin() as quota_db:
            count = (await quota_db.execute(upsert)).scalar_one_or_none()
    else:
        count = (await db.execute(upsert)).scalar_one_or_none()
    if count is None:
        raise Problem(429, "RATE_LIMITED")


def remote_identity(request: Request) -> str:
    from ipaddress import ip_address, ip_network

    remote = request.client.host if request.client else "unknown"
    proxies = [ip_network(value) for value in get_settings().trusted_proxies]
    try:
        peer = ip_address(remote)
        if not any(peer in network for network in proxies):
            return remote
        chain = request.headers.get("x-forwarded-for", "").split(",")
        if len(chain) > 10:
            return remote
        for value in reversed(chain):
            address = ip_address(value.strip())
            if not any(address in network for network in proxies):
                return str(address)
    except ValueError:
        return remote
    return remote


async def issue_session(
    db: AsyncSession,
    response: Response,
    audience: str,
    user_id: UUID | None = None,
    actor_id: UUID | None = None,
) -> LoginSession:
    token = secrets.token_urlsafe(32)
    lifetime = 12 if audience == "staff" else 24
    session = LoginSession(
        token_hash=digest(token),
        staff_user_id=user_id,
        visitor_actor_id=actor_id,
        csrf_secret=secrets.token_urlsafe(32),
        last_seen_at=now(),
        expires_at=now() + timedelta(hours=lifetime),
    )
    db.add(session)
    settings = get_settings()
    response.set_cookie(
        settings.cookie_name(audience),
        token,
        max_age=lifetime * 3600,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return session


async def revoke_existing(db: AsyncSession, request: Request, audience: str) -> None:
    token = request.cookies.get(get_settings().cookie_name(audience))
    if token:
        session = await db.scalar(
            select(LoginSession).where(LoginSession.token_hash == digest(token))
        )
        if session:
            session.revoked_at = now()


async def resolve(db: AsyncSession, request: Request, audience: str) -> Principal:
    token = request.cookies.get(get_settings().cookie_name(audience))
    if not token:
        raise Problem(401, "AUTH_REQUIRED")
    session = await db.scalar(
        select(LoginSession).where(LoginSession.token_hash == digest(token))
    )
    if not session or session.revoked_at or session.expires_at <= now():
        raise Problem(401, "SESSION_EXPIRED")
    if audience == "staff":
        if not session.staff_user_id:
            raise Problem(401, "AUTH_REQUIRED")
        if session.last_seen_at + timedelta(minutes=30) <= now():
            raise Problem(401, "SESSION_EXPIRED")
        user = await db.get(StaffUser, session.staff_user_id)
        if not user or not user.active:
            raise Problem(401, "AUTH_REQUIRED")
        principal = Principal(session, audience, user=user)
    else:
        if not session.visitor_actor_id:
            raise Problem(401, "AUTH_REQUIRED")
        actor = await db.get(Actor, session.visitor_actor_id)
        if not actor or not actor.active or actor.kind != "visitor":
            raise Problem(401, "AUTH_REQUIRED")
        await active_workspace(db, actor.workspace_id)
        principal = Principal(session, audience, actor=actor)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        if not secrets.compare_digest(
            request.headers.get("x-csrf-token", ""), session.csrf_secret
        ):
            raise Problem(403, "CSRF_REJECTED")
    session.last_seen_at = now()
    return principal


async def active_workspace(db: AsyncSession, workspace_id: UUID) -> Workspace:
    workspace = await db.get(Workspace, workspace_id)
    if not workspace or (workspace.expires_at and workspace.expires_at <= now()):
        raise Problem(404, "RESOURCE_NOT_FOUND")
    return workspace


async def workspace_actor(
    db: AsyncSession, principal: Principal, workspace_id: UUID
) -> Actor:
    await active_workspace(db, workspace_id)
    if principal.actor:
        if principal.actor.workspace_id == workspace_id:
            return principal.actor
    elif principal.user:
        actor = await db.scalar(
            select(Actor).where(
                Actor.workspace_id == workspace_id,
                Actor.user_id == principal.user.id,
                Actor.kind == "staff",
                Actor.active.is_(True),
            )
        )
        if actor:
            return actor
    raise Problem(404, "RESOURCE_NOT_FOUND")


async def session_view(db: AsyncSession, principal: Principal) -> SessionView:
    memberships = []
    if principal.user:
        rows = (
            await db.execute(
                select(Actor, Workspace)
                .join(Workspace)
                .where(
                    Actor.user_id == principal.user.id,
                    Actor.active.is_(True),
                )
            )
        ).all()
        memberships = [
            Membership(
                workspace_id=w.id,
                actor_id=a.id,
                name=w.name,
                role=a.role or "",
                fictional_data=w.fictional_data,
            )
            for a, w in rows
            if not w.expires_at or w.expires_at > now()
        ]
    workspace = (
        await db.get(Workspace, principal.actor.workspace_id)
        if principal.actor
        else None
    )
    return SessionView(
        audience="staff" if principal.user else "visitor",
        csrf_token=principal.session.csrf_secret,
        expires_at=principal.session.expires_at,
        actor_id=principal.actor.id if principal.actor else None,
        workspace_id=principal.actor.workspace_id if principal.actor else None,
        public_key=workspace.public_key if workspace else None,
        memberships=memberships,
        provider_mode=get_settings().llm_provider,
        fictional_data=bool(workspace and workspace.fictional_data)
        or bool(memberships and all(m.fictional_data for m in memberships)),
        ai_available=get_settings().ai_enabled_for_public(),
    )
