import json
import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from supportdesk.api.errors import Problem, problem_handler
from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session
from supportdesk.infrastructure.logging import configure_logging
from supportdesk.infrastructure.metrics import http_latency, http_requests
from supportdesk.modules.conversations.routes import router as conversation_router
from supportdesk.modules.identity.routes import router
from supportdesk.modules.knowledge.routes import router as knowledge_router
from supportdesk.modules.realtime.endpoint import router as realtime_router


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="SupportDesk", version="0.1.0")
    app.add_exception_handler(Problem, problem_handler)  # type: ignore[arg-type]

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> Response:
        return await problem_handler(
            request,
            Problem(
                422,
                "VALIDATION_ERROR",
                fields=[list(item["loc"]) for item in exc.errors()],
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> Response:
        return await problem_handler(
            request,
            Problem(
                exc.status_code,
                "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> Response:
        return await problem_handler(request, Problem(503, "DATABASE_UNAVAILABLE"))

    app.include_router(router)
    app.include_router(conversation_router)
    app.include_router(realtime_router)
    app.include_router(knowledge_router)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        route = getattr(request.scope.get("route"), "path", "unmatched")
        http_requests.labels(request.method, route, str(response.status_code)).inc()
        http_latency.labels(request.method, route).observe(
            time.perf_counter() - started
        )
        logging.getLogger("supportdesk.http").info(
            json.dumps(
                {
                    "event": "http.completed",
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "route": route,
                    "status": response.status_code,
                }
            )
        )
        return response

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/health/ready")
    async def ready() -> dict[str, str]:
        try:
            async with Session() as db:
                revision = await db.scalar(
                    text("SELECT version_num FROM alembic_version")
                )
            if revision != "0007":
                raise Problem(503, "SCHEMA_INCOMPATIBLE")
        except Problem:
            raise
        except Exception as exc:
            raise Problem(503, "DATABASE_UNAVAILABLE") from exc
        redis_state = "ok"
        redis = Redis.from_url(
            get_settings().redis_url, socket_connect_timeout=0.2, socket_timeout=0.2
        )
        try:
            await redis.ping()
        except Exception:
            redis_state = "degraded"
        finally:
            await redis.aclose()
        return {
            "status": "ok",
            "schema": revision,
            "redis": redis_state,
            "provider": get_settings().llm_provider,
        }

    return app
