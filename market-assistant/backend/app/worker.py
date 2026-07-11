# worker.py = the arq entrypoint (WorkerSettings + lifecycle hooks).
# app/workers/ = the job implementations (e.g. news_worker.run_news_ingest).
from datetime import UTC, datetime, timedelta
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from arq.cron import CronJob
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import get_redis, get_sessionmaker
from app.ingest.backfill import backfill_gaps
from app.ingest.equity_poller import poll_equity_universe
from app.models.instrument import Instrument
from app.strategies.worker import on_candle_close_job
from app.workers.backtest_worker import run_backtest_job
from app.workers.news_worker import run_news_ingest

# Rolling window the periodic sweep re-checks for gaps on each active instrument.
_BACKFILL_SWEEP_WINDOW = timedelta(hours=1)
_BACKFILL_SWEEP_TF = "1m"


async def trigger_backfill_sweep(ctx: dict[str, Any]) -> int:
    """Periodic cron trigger: for every active instrument, detect and fill any
    gaps in the trailing window via ``backfill_gaps`` (same ctx contract)."""
    session_factory = ctx["session_factory"]
    async with session_factory() as session:
        result = await session.execute(
            select(Instrument.id, Instrument.symbol).where(Instrument.active.is_(True))
        )
        instruments = result.all()

    end_ts = datetime.now(UTC)
    start_ts = end_ts - _BACKFILL_SWEEP_WINDOW
    total = 0
    for instrument_id, symbol in instruments:
        total += await backfill_gaps(
            ctx, instrument_id, symbol, _BACKFILL_SWEEP_TF, start_ts, end_ts
        )
    return total


async def on_startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    ctx["session_factory"] = get_sessionmaker()
    ctx["redis"] = get_redis()
    ctx["backfill_rate_limit_ms"] = settings.BACKFILL_RATE_LIMIT_MS
    # Import ccxt lazily so merely importing this module (e.g. in tests that
    # only inspect WorkerSettings) never pulls in the network client.
    import ccxt.async_support as ccxt_async

    ctx["exchange"] = ccxt_async.binance({"enableRateLimit": True})


async def on_shutdown(ctx: dict[str, Any]) -> None:
    exchange = ctx.get("exchange")
    if exchange is not None:
        await exchange.close()


class WorkerSettings:
    """arq worker definition. Run with ``arq app.worker.WorkerSettings``."""

    redis_settings: RedisSettings = RedisSettings.from_dsn(get_settings().redis_url)
    functions: list[Any] = [
        backfill_gaps,
        run_backtest_job,
        on_candle_close_job,
        poll_equity_universe,
    ]
    cron_jobs: list[CronJob] = [
        cron(run_news_ingest, minute=set(range(0, 60, 15)), run_at_startup=False),
        cron(trigger_backfill_sweep, minute={7, 37}),
        cron(poll_equity_universe, minute=set(range(0, 60, 15))),
    ]
    on_startup = staticmethod(on_startup)
    on_shutdown = staticmethod(on_shutdown)
