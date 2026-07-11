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

## Deployment (Phase 12)

Free-tier public hosting, split by workload:

| Piece | Host | Why |
|---|---|---|
| Frontend (static SPA) | **Vercel** (Hobby) | CDN + SPA rewrites; `vercel.json` |
| Backend (API + WS + arq worker) | **Hugging Face Space** (Docker) | Needs *always-on* compute for WebSockets + the background worker; 16GB free fits the local ML models |
| Postgres + `pgvector` | Neon / Supabase (free) | |
| Redis | Upstash (free) | |

The backend runs one container with `PROCESS_TYPE=all` (web + worker together —
see `backend/docker-entrypoint.sh`). The same `backend/Dockerfile` is host-agnostic,
so any container host (Fly.io, Render, a VM) can run it if you outgrow the free tier.

**Free-tier survival guards** (all in this phase):
- **Fail-fast config** — in `ENV=prod`, missing secrets crash startup with a
  readable error instead of serving a broken app (`backend/app/core/config.py`).
- **Universe cap** — ≤25 crypto symbols + NIFTY-50 equities, enforced before
  ingestion subscribes (`backend/app/core/universe.py`).
- **Candle retention** — a daily job drops 1m candles older than 60 days
  (`backend/app/core/retention.py`).
- **LLM quota guard** — a global daily cap protects the free provider budget
  (`backend/app/chat/quota.py`).

**Pipeline** (`.github/workflows/deploy.yml`): on merge to `main`, run the full CI
gate → upload backend to the HF Space + `vercel deploy --prod` → post-deploy smoke
(`pytest -m smoke`) against the live URLs. PRs get a Vercel preview URL commented back.

### One-time setup (manual)

1. **Neon/Supabase** — create a Postgres DB, enable `pgvector`; **Upstash** — create a Redis DB.
2. **HF Space** — create a Docker Space; in *Settings → Variables and secrets* set
   `ENV=prod`, `PROCESS_TYPE=all`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`,
   `LLM_PROVIDER` + its key, `TELEGRAM_BOT_TOKEN`, `CORS_ALLOWED_ORIGINS` (the Vercel origin).
   See `backend/README.md`.
3. **Vercel** — `cd frontend && vercel link`; set `VITE_API_URL`/`VITE_WS_URL`
   (HF Space URL) + `VITE_SUPABASE_*` for Production and Preview scopes.
4. **GitHub Actions secrets** — `HF_TOKEN`, `HF_SPACE_ID`, `VERCEL_TOKEN`,
   `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `STAGING_URL`, `STAGING_WS_URL`, `STAGING_FRONTEND_URL`.

## Status

Phases 1–11 complete (ingestion, charts, scanner, backtesting, strategy presets,
trend/regime, multi-asset stocks, ML predictions, AI chatbot, alerts/auth).
**Phase 12 — Deployment:** fail-fast config + free-tier survival guards + Docker
image + Vercel/HF-Space deploy pipeline + smoke/acceptance gates shipped; live
public deploy pending the one-time setup above.
