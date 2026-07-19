"""Session-aware, idempotent NIFTY-50 equity poller (arq task).

Runs on a 15-minute cron. Outside NSE trading hours it is a no-op. Inside a
session it refreshes the trailing window of 1-minute candles for every equity
instrument via ``fetch_candles`` and persists them with ``upsert_candles``,
which is idempotent on ``(instrument_id, tf, ts)`` and (when a Redis handle is
supplied) fans each written candle out over Phase-3 pub/sub.
"""

from datetime import datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.ingest.nse_calendar import IST, is_in_session
from app.ingest.universe_equity import ensure_equity_instruments
from app.ingest.writer import upsert_candles
from app.ingest.yfinance_adapter import fetch_candles

POLL_TF = "1m"


async def poll_equity_universe(ctx: dict[str, Any]) -> int:
    """Poll the NIFTY-50 equity universe for fresh 1m candles.

    Returns the total number of candles upserted. Returns 0 when called
    outside an NSE trading session (weekend/holiday/pre-open/post-close).
    """
    settings = get_settings()
    now = datetime.now(IST)

    if not is_in_session(now):
        return 0

    redis = ctx["redis"]

    # Context-manage the session so its connection is returned to the pool on
    # every tick (and on any error mid-loop); a bare factory() call leaked one
    # connection per 15-minute run.
    async with ctx["session_factory"]() as session:
        instruments = await ensure_equity_instruments(session)

        start = now - timedelta(minutes=settings.EQUITY_POLL_INTERVAL_MIN)
        total_written = 0

        for instrument in instruments:
            raw_symbol = instrument.symbol.removesuffix(".NS")
            candles = fetch_candles(raw_symbol, POLL_TF, start, now)
            if not candles:
                continue
            # upsert_candles fans out each candle via publish_candle_update when
            # redis is passed, so we do NOT publish separately here.
            written = await upsert_candles(session, instrument.id, candles, redis=redis)
            total_written += written

        await session.commit()
        return total_written
