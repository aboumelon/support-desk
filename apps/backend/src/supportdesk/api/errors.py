from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class Problem(Exception):
    def __init__(self, status: int, code: str, **details: Any):
        self.status = status
        self.code = code
        self.details = details


async def problem_handler(request: Request, exc: Problem) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        media_type="application/problem+json",
        headers={"Retry-After": "60"} if exc.status == 429 else {},
        content={
            "type": "about:blank",
            "title": exc.code.replace("_", " ").title(),
            "status": exc.status,
            "code": exc.code,
            "request_id": getattr(request.state, "request_id", ""),
            "details": exc.details,
        },
    )
