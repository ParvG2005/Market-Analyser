# Phase 12 Task 2: single image, two process types (web / worker) via entrypoint.
FROM python:3.12-slim AS base

WORKDIR /app

# libgomp1: LightGBM runtime; libpq/build-essential: asyncpg + native wheels; curl: healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Install deps first (better layer caching). setuptools packages.find resolves `app`.
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system --no-cache .

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

ENV PROCESS_TYPE=web
ENV PORT=8080

ENTRYPOINT ["./docker-entrypoint.sh"]
