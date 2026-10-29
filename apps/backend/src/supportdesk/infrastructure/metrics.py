from collections.abc import Iterator

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from prometheus_client.core import GaugeMetricFamily, Metric
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from supportdesk.infrastructure.database import Session


class SnapshotCollector:
    def __init__(self, families: list[GaugeMetricFamily]) -> None:
        self.families = families

    def collect(self) -> Iterator[Metric]:
        return iter(self.families)


http_requests = Counter(
    "supportdesk_http_requests_total",
    "HTTP requests by bounded route template",
    ["method", "route", "status"],
)
http_latency = Histogram(
    "supportdesk_http_request_seconds",
    "HTTP latency by route template",
    ["method", "route"],
)
open_sockets = Gauge("supportdesk_open_sockets", "Open sockets in this API process")
socket_connections = Counter("supportdesk_socket_connections_total", "Accepted sockets")
socket_overflows = Counter(
    "supportdesk_socket_overflows_total", "Slow consumer disconnects"
)
replayed_events = Counter(
    "supportdesk_replayed_events_total", "Durable events queued for sockets"
)
event_lag = Histogram(
    "supportdesk_event_delivery_seconds", "Commit to socket enqueue latency"
)


async def operational_metrics() -> bytes:
    """Read shared durable gauges; API-local counters are exported separately."""
    registry = CollectorRegistry()
    available = GaugeMetricFamily(
        "supportdesk_metrics_database_available", "Durable metrics query succeeded"
    )
    families: list[GaugeMetricFamily] = []
    try:
        async with Session.begin() as db:
            await db.execute(text("SET TRANSACTION READ ONLY"))
            await db.execute(text("SET LOCAL statement_timeout = '2000'"))
            backlog = (
                await db.execute(
                    text("""
                SELECT count(*) AS pending,
                  coalesce(greatest(extract(epoch FROM
                    now()-min(created_at)),0),0) AS age
                FROM outbox WHERE status='pending'
            """)
                )
            ).one()
            pending = GaugeMetricFamily(
                "supportdesk_outbox_pending", "Unpublished durable outbox rows"
            )
            pending.add_metric([], backlog.pending)
            age = GaugeMetricFamily(
                "supportdesk_outbox_oldest_seconds", "Oldest unpublished row age"
            )
            age.add_metric([], float(backlog.age))
            families += [pending, age]
            jobs = GaugeMetricFamily(
                "supportdesk_jobs",
                "Retained jobs by bounded state and kind",
                labels=["kind", "status"],
            )
            queue_age = GaugeMetricFamily(
                "supportdesk_job_queue_oldest_seconds",
                "Oldest due queued job age",
                labels=["kind"],
            )
            expired = GaugeMetricFamily(
                "supportdesk_job_expired_leases", "Running jobs with an expired lease"
            )
            for row in await db.execute(
                text("""
                SELECT CASE WHEN kind IN ('ai','ingestion')
                  THEN kind ELSE 'other' END AS kind,
                  status, count(*) AS amount FROM jobs GROUP BY 1,2
            """)
            ):
                jobs.add_metric([row.kind, row.status], row.amount)
            for row in await db.execute(
                text("""
                SELECT CASE WHEN kind IN ('ai','ingestion')
                  THEN kind ELSE 'other' END AS kind,
                  greatest(extract(epoch FROM now()-min(available_at)),0) AS age
                FROM jobs WHERE status IN ('pending','retry') AND available_at <= now()
                GROUP BY 1
            """)
            ):
                queue_age.add_metric([row.kind], float(row.age))
            expired.add_metric(
                [],
                await db.scalar(
                    text(
                        "SELECT count(*) FROM jobs WHERE status='running' "
                        "AND leased_until < now()"
                    )
                )
                or 0,
            )
            families += [jobs, queue_age, expired]
            runs = GaugeMetricFamily(
                "supportdesk_ai_runs",
                "Retained runs by bounded state",
                labels=["status"],
            )
            for row in await db.execute(
                text("""
                SELECT CASE WHEN status IN
                  ('queued','running','succeeded','failed','superseded')
                  THEN status ELSE 'other' END AS status, count(*) AS amount
                FROM ai_runs GROUP BY 1
            """)
            ):
                runs.add_metric([row.status], row.amount)
            usage = GaugeMetricFamily(
                "supportdesk_ai_usage_tokens",
                "Retained known tokens and conservative unresolved charges",
                labels=["state"],
            )
            unknown = GaugeMetricFamily(
                "supportdesk_ai_unknown_usage_attempts",
                "Provider attempts whose usage remains unknown",
            )
            tokens = (
                await db.execute(
                    text("""
                SELECT coalesce(sum(a.input_tokens+a.output_tokens)
                  FILTER (WHERE a.usage_state='known'),0) AS known,
                  coalesce(sum(r.per_attempt_tokens)
                  FILTER (WHERE a.usage_state='unknown'),0) AS unresolved,
                  count(*) FILTER (WHERE a.usage_state='unknown') AS unknown
                FROM ai_attempts a JOIN ai_runs r ON r.id=a.run_id
            """)
                )
            ).one()
            usage.add_metric(["known"], tokens.known)
            usage.add_metric(["unresolved_reserved"], tokens.unresolved)
            unknown.add_metric([], tokens.unknown)
            families += [runs, usage, unknown]
            duration = GaugeMetricFamily(
                "supportdesk_ai_recent_seconds",
                "Mean retained duration for the last 24 hours; zero when absent",
                labels=["phase"],
            )
            timing = (
                await db.execute(
                    text("""
                SELECT (SELECT coalesce(avg(greatest(extract(epoch
                    FROM a.created_at-j.created_at),0)),0)
                  FROM ai_attempts a JOIN ai_runs r ON r.id=a.run_id
                  JOIN jobs j ON j.id=r.job_id
                  WHERE a.attempt=1 AND a.created_at > now()-interval '24 hours')
                  AS queue,
                  (SELECT coalesce(avg(extract(epoch FROM finished_at-created_at)),0)
                  FROM ai_runs WHERE finished_at > now()-interval '24 hours') AS total
            """)
                )
            ).one()
            duration.add_metric(["queue"], float(timing.queue))
            duration.add_metric(["total"], float(timing.total))
            families.append(duration)
        available.add_metric([], 1)
    except SQLAlchemyError:
        families = []
        available.add_metric([], 0)
    registry.register(SnapshotCollector([available, *families]))
    return generate_latest(registry)
