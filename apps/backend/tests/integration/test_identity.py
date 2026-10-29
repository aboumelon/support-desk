from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import select, update

from supportdesk.cli.seed_demo import seed
from supportdesk.infrastructure.database import Session, now
from supportdesk.modules.identity.models import LoginSession


async def test_demo_audiences_and_csrf(client: AsyncClient):
    response = await client.post("/api/v1/public/demo")
    assert response.status_code == 200
    visitor = response.json()
    staff = (await client.get("/api/v1/auth/staff/me")).json()
    assert staff["memberships"][0]["workspace_id"] == visitor["workspace_id"]
    assert visitor["csrf_token"] != staff["csrf_token"]
    assert set(client.cookies.keys()) == {"sd_staff", "sd_visitor"}
    assert (await client.post("/api/v1/customer/logout")).status_code == 403
    assert (
        await client.post(
            "/api/v1/customer/logout", headers={"X-CSRF-Token": staff["csrf_token"]}
        )
    ).status_code == 403
    assert (
        await client.post(
            "/api/v1/customer/logout", headers={"X-CSRF-Token": visitor["csrf_token"]}
        )
    ).status_code == 204
    assert (await client.get("/api/v1/customer/session")).status_code == 401
    assert (await client.get("/api/v1/auth/staff/me")).status_code == 200


async def test_workspace_isolation_and_revocation(client: AsyncClient):
    first = (await client.post("/api/v1/public/demo")).json()
    old_token = client.cookies["sd_staff"]
    second = (await client.post("/api/v1/public/demo")).json()
    assert first["workspace_id"] != second["workspace_id"]
    assert (
        await client.get(f"/api/v1/staff/workspaces/{first['workspace_id']}")
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/staff/workspaces/{second['workspace_id']}")
    ).status_code == 200
    client.cookies.set("sd_staff", old_token, domain="test.local", path="/")
    assert (await client.get("/api/v1/auth/staff/me")).status_code == 401


async def test_expiry_and_token_hash(client: AsyncClient):
    await client.post("/api/v1/public/demo")
    token = client.cookies["sd_visitor"]
    async with Session.begin() as db:
        sessions = (await db.scalars(select(LoginSession))).all()
        assert all(s.token_hash != token and len(s.token_hash) == 64 for s in sessions)
        await db.execute(
            update(LoginSession).values(expires_at=now() - timedelta(seconds=1))
        )
    assert (await client.get("/api/v1/customer/session")).status_code == 401
    assert (await client.get("/api/v1/auth/staff/me")).status_code == 401


async def test_origin_rate_limit_and_login(client: AsyncClient):
    await seed()
    assert (
        await client.post(
            "/api/v1/public/demo", headers={"Origin": "https://evil.invalid"}
        )
    ).status_code == 403
    payload = {"email": "admin@naran.invalid", "password": "wrong"}
    assert (
        await client.post("/api/v1/auth/staff/login", json=payload)
    ).status_code == 401
    payload["password"] = "Fictional-Demo-Only-2026!"
    result = await client.post("/api/v1/auth/staff/login", json=payload)
    assert result.status_code == 200
    assert len(result.json()["memberships"]) == 1
    for _ in range(4):
        result = await client.post("/api/v1/auth/staff/login", json=payload)
    assert result.status_code == 429
    assert result.headers["retry-after"] == "60"


async def test_staff_cookie_cannot_authenticate_customer(client: AsyncClient):
    await client.post("/api/v1/public/demo")
    client.cookies.set(
        "sd_visitor", client.cookies["sd_staff"], domain="test.local", path="/"
    )
    assert (await client.get("/api/v1/customer/session")).status_code == 401
