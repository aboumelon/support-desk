from datetime import timedelta
from uuid import UUID, uuid4

from supportdesk.infrastructure.database import Session, now
from supportdesk.modules.jobs.models import Job, Outbox


async def test_operational_metrics_report_durable_backlog_without_identifiers(client):
    identity = (await client.post("/api/v1/public/demo")).json()
    workspace = UUID(identity["workspace_id"])
    async with Session.begin() as db:
        db.add(
            Job(
                workspace_id=workspace,
                kind="unrecognized-fixture-kind",
                resource_id=uuid4(),
                logical_key=str(uuid4()),
                status="running",
                attempt=2,
                leased_until=now() - timedelta(seconds=100),
            )
        )
        db.add(
            Outbox(
                workspace_id=workspace,
                kind="notification",
                reference_id=uuid4(),
                dedupe_key=str(uuid4()),
                created_at=now() - timedelta(seconds=60),
            )
        )
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "supportdesk_metrics_database_available 1.0" in response.text
    assert 'supportdesk_jobs{kind="other",status="running"} 1.0' in response.text
    assert "supportdesk_job_expired_leases 1.0" in response.text
    assert "supportdesk_outbox_pending 1.0" in response.text
    age = next(
        line
        for line in response.text.splitlines()
        if line.startswith("supportdesk_outbox_oldest_seconds ")
    )
    assert float(age.split()[1]) >= 60
    assert str(workspace) not in response.text
    assert "unrecognized-fixture-kind" not in response.text
