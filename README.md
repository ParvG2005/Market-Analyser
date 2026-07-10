# Market Analysis Assistant

A deployable, multi-asset (crypto + stocks) **analysis-only** platform: real-time
dashboard, market visualization, a scanner engine, backtested strategy presets,
trend/regime detection, ML signal probabilities, and an AI chatbot helper grounded
in live market data.

> **Educational analysis. Not investment advice. Past performance ≠ future results.**
> No money moves through this system — no order execution, no broker connections,
> no simulated accounts. Pure analysis, education, and decision support.

## Stack

| Layer | Tool |
|---|---|
| Backend API | FastAPI (Python 3.12), async SQLAlchemy 2.0 + asyncpg, Alembic |
| Database | PostgreSQL 16 + `pgvector` |
| Cache / pub-sub | Redis |
| Frontend | React 18 + Vite + TypeScript, zustand, TanStack Query, react-router |
| CI | GitHub Actions (ruff · mypy · pytest · eslint · tsc · vitest) |

## Monorepo layout

```
market-assistant/
├── backend/          FastAPI service (app factory, config, deps, api, models, alembic)
│   └── tests/        unit · integration · acceptance
├── frontend/         React + Vite + TS SPA (pages, stores, lib)
└── docker-compose.yml  local Postgres(+pgvector) + Redis
```

## Local development

Start infra (Postgres on host port **5434**, Redis on **6379**):

```bash
cd market-assistant
docker compose up -d
```

Backend (Python 3.12 via [uv](https://github.com/astral-sh/uv)):

```bash
cd market-assistant/backend
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
alembic upgrade head
ruff check . && mypy app && pytest -v
```

Frontend:

```bash
cd market-assistant/frontend
npm install
npm run lint && npm run typecheck && npm run test
```

## Status

- **Phase 1 — Skeleton, CI, Local Infra: complete.** Monorepo scaffold, backend
  (config, `GET /health`, full Alembic schema incl. pgvector), frontend scaffold
  (7 routed pages), and a green GitHub Actions CI pipeline.
- Later phases (ingestion, charts, scanner, backtesting, strategies, trend/regime,
  multi-asset, ML, chatbot, alerts/auth, deployment) build on this skeleton.
