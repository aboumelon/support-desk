import json
import logging
from typing import Any


def configure_logging() -> None:
    logger = logging.getLogger("supportdesk")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def job_event(event: str, **fields: Any) -> None:
    logging.getLogger("supportdesk.jobs").info(json.dumps({"event": event, **fields}))
