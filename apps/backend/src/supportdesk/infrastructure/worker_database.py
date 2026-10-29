from functools import lru_cache

from sqlalchemy import Engine, create_engine

from supportdesk.config import get_settings


@lru_cache
def worker_engine() -> Engine:
    # First used in the worker child, after Celery forks.
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        pool_size=3,
    )
