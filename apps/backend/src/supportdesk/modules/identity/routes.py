import secrets
from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from supportdesk.api.errors import Problem
from supportdesk.config import get_settings
from supportdesk.infrastructure.database import get_db, now
from supportdesk.modules.identity.models import StaffUser
from supportdesk.modules.identity.schemas import (
    LoginInput,
    PublicCapabilities,
    SessionView,
    WorkspaceView,
)
from supportdesk.modules.identity.service import (
    DUMMY_HASH,
    Principal,
    check_origin,
    issue_session,
    passwords,
    rate_limit,
    remote_identity,
    resolve,
    revoke_existing,
    session_view,
    workspace_actor,
)
from supportdesk.modules.workspaces.models import Actor, Workspace

router = APIRouter(prefix="/api/v1")
DB = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/public/capabilities",
    response_model=PublicCapabilities,
    response_model_exclude_none=True,
)
async def capabilities(db: DB) -> PublicCapabilities:
    settings = get_settings()
    customer_entry_key = None
    if settings.app_env != "production":
        customer_entry_key = await db.scalar(
            select(Workspace.public_key).where(
                Workspace.public_key == "tarvio-demo",
                Workspace.fictional_data.is_(True),
                Workspace.expires_at.is_(None),
            )
        )
    return PublicCapabilities(
        demo_available=settings.demo_mode,
        customer_entry_key=customer_entry_key,
        ai_mode=(
            "disabled"
            if not settings.ai_enabled_for_public()
            else "simulated"
            if settings.llm_provider == "fake"
            else "live"
        ),
    )


@router.post("/auth/staff/login", response_model=SessionView)
async def login(
    body: LoginInput, request: Request, response: Response, db: DB
) -> SessionView:
    check_origin(request)
    email = body.email.strip().casefold()
    # Limit all login attempts, including successful attempts.
    await rate_limit("login", email + ":" + remote_identity(request), 5)
    user = await db.scalar(select(StaffUser).where(StaffUser.normalized_email == email))
    password_hash = user.password_hash if user else DUMMY_HASH
    await db.commit()
    valid = await run_in_threadpool(passwords.verify, body.password, password_hash)
    if not user or not user.active or not valid:
        raise Problem(401, "INVALID_CREDENTIALS")
    await revoke_existing(db, request, "staff")
    session = await issue_session(db, response, "staff", user_id=user.id)
    result = await session_view(db, Principal(session, "staff", user=user))
    await db.commit()
    return result


@router.get("/auth/staff/me", response_model=SessionView)
async def staff_me(request: Request, db: DB) -> SessionView:
    result = await session_view(db, await resolve(db, request, "staff"))
    await db.commit()
    return result


@router.get("/customer/session", response_model=SessionView)
async def customer_me(request: Request, db: DB) -> SessionView:
    result = await session_view(db, await resolve(db, request, "visitor"))
    await db.commit()
    return result


@router.post("/auth/staff/logout", status_code=204)
async def staff_logout(request: Request, response: Response, db: DB) -> None:
    principal = await resolve(db, request, "staff")
    principal.session.revoked_at = now()
    await db.commit()
    response.delete_cookie(get_settings().cookie_name("staff"), path="/")


@router.post("/customer/logout", status_code=204)
async def customer_logout(request: Request, response: Response, db: DB) -> None:
    principal = await resolve(db, request, "visitor")
    principal.session.revoked_at = now()
    await db.commit()
    response.delete_cookie(get_settings().cookie_name("visitor"), path="/")


@router.post(
    "/public/workspaces/{public_key}/visitor-sessions", response_model=SessionView
)
async def visitor(
    public_key: str, request: Request, response: Response, db: DB
) -> SessionView:
    check_origin(request)
    await rate_limit("session", remote_identity(request), 5)
    workspace = await db.scalar(
        select(Workspace).where(Workspace.public_key == public_key)
    )
    if not workspace or (workspace.expires_at and workspace.expires_at <= now()):
        raise Problem(404, "RESOURCE_NOT_FOUND")
    if (
        get_settings().app_env == "production"
        and workspace.fictional_data
        and workspace.expires_at is None
    ):
        raise Problem(404, "RESOURCE_NOT_FOUND")
    actor = Actor(
        workspace_id=workspace.id, kind="visitor", display_name="Demo customer"
    )
    db.add(actor)
    await db.flush()
    await revoke_existing(db, request, "visitor")
    session = await issue_session(db, response, "visitor", actor_id=actor.id)
    result = await session_view(db, Principal(session, "visitor", actor=actor))
    await db.commit()
    return result


@router.get("/staff/workspaces/{workspace_id}", response_model=WorkspaceView)
async def workspace_details(
    workspace_id: UUID, request: Request, db: DB
) -> WorkspaceView:
    actor = await workspace_actor(db, await resolve(db, request, "staff"), workspace_id)
    workspace = await db.get(Workspace, workspace_id)
    assert workspace is not None
    result = WorkspaceView(
        id=workspace.id,
        name=workspace.name,
        public_key=workspace.public_key,
        role=actor.role,
        ai_enabled=workspace.ai_enabled,
    )
    await db.commit()
    return result


@router.post("/public/demo", response_model=SessionView)
async def demo(request: Request, response: Response, db: DB) -> SessionView:
    check_origin(request)
    if not get_settings().demo_mode:
        raise Problem(404, "RESOURCE_NOT_FOUND")
    await rate_limit("session", remote_identity(request), 5)
    # Each browser demo gets its own staff identity and workspace; no shared privileges.
    await rate_limit("demo-global", "all", get_settings().demo_daily_limit, 86400)
    await db.execute(text("SELECT pg_advisory_xact_lock(76124912, 2)"))
    active = await db.scalar(
        select(func.count()).select_from(Workspace).where(Workspace.expires_at > now())
    )
    if (active or 0) >= get_settings().demo_active_limit:
        raise Problem(429, "DEMO_CAPACITY_REACHED")
    workspace = Workspace(
        public_key=secrets.token_urlsafe(18),
        name="Tarvio Cloud (fictional)",
        fictional_data=True,
        expires_at=now() + timedelta(hours=24),
    )
    user = StaffUser(
        normalized_email=f"{secrets.token_hex(16)}@demo.invalid",
        password_hash=DUMMY_HASH,
    )
    db.add_all([workspace, user])
    await db.flush()
    customer = Actor(
        workspace_id=workspace.id, kind="visitor", display_name="Demo customer"
    )
    db.add_all(
        [
            customer,
            Actor(
                workspace_id=workspace.id,
                kind="staff",
                user_id=user.id,
                role="admin",
                display_name="Demo operator",
            ),
            Actor(
                workspace_id=workspace.id,
                kind="assistant",
                display_name="Fixture assistant",
            ),
        ]
    )
    await db.flush()
    from supportdesk.modules.knowledge.demo import clone_fictional_knowledge

    await clone_fictional_knowledge(db, workspace)
    for audience in ["staff", "visitor"]:
        await revoke_existing(db, request, audience)
    await issue_session(db, response, "staff", user_id=user.id)
    session = await issue_session(db, response, "visitor", actor_id=customer.id)
    result = await session_view(db, Principal(session, "visitor", actor=customer))
    await db.commit()
    return result
