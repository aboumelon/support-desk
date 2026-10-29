from celery import Celery

from supportdesk.config import get_settings
from supportdesk.infrastructure.logging import configure_logging

configure_logging()

app = Celery(
    "supportdesk",
    broker=get_settings().redis_url,
    include=["supportdesk.workers.tasks"],
)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={
        "visibility_timeout": 900,
        "global_keyprefix": "sd:broker:",
    },
    task_soft_time_limit=270,
    task_time_limit=300,
    task_default_queue="ingestion",
    broker_connection_retry_on_startup=True,
)
