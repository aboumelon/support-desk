FROM python:3.13.14-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_HTTP_TIMEOUT=120 UV_CONCURRENT_DOWNLOADS=2 UV_LINK_MODE=copy
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-install-project --no-dev
COPY apps/backend/src ./src
COPY apps/backend/migrations ./migrations
COPY apps/backend/alembic.ini ./
COPY evals ./evals
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev
RUN useradd --uid 10001 --create-home app && mkdir -p /var/lib/supportdesk/files /var/lib/supportdesk/models && chown -R app:app /var/lib/supportdesk
ENV PATH="/app/.venv/bin:$PATH" APP_ENV=production STORAGE_ROOT=/var/lib/supportdesk/files MODEL_CACHE=/var/lib/supportdesk/models
USER app
CMD ["uvicorn","supportdesk.main:create_app","--factory","--host","0.0.0.0","--port","8000","--no-access-log","--no-proxy-headers"]
FROM base AS worker
USER root
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --extra worker --no-dev
USER app
CMD ["celery","-A","supportdesk.workers.celery_app:app","worker","-Q","ai,ingestion","--concurrency=1"]
