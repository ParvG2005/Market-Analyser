"""App ingest entrypoint: compose universe selection, WS consumption, and the
candle flush loop into one long-running task (``arq app.worker`` runs the
cron/backfill side; this is the live-stream side)."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.deps import get_redis, get_sessionmaker
from app.ingest.buffer import CandleBuffer, SessionFactory
from app.ingest.metrics import SupportsRedisKV
from app.ingest.universe import SupportsFetchTickers, get_top_n_by_volume
from app.ingest.ws_consumer import BinanceWSConsumer, WSConnection
from app.models.instrument import Instrument

logger = logging.getLogger(__name__)

_EXCHANGE = "binance"
_ASSET_CLASS = "crypto"


async def _ensure_instruments(
    session_factory: SessionFactory, symbols: list[str]
) -> dict[str, int]:
    """Get-or-create an Instrument per symbol; return symbol -> id map.

    Upsert ON CONFLICT (symbol, exchange) DO NOTHING then read the ids back, so
    concurrent runners converge on the same rows without racing on inserts.
    """
    if not symbols:
        return {}
    async with session_factory() as session:
        stmt = insert(Instrument).values(
            [
                {"symbol": s, "asset_class": _ASSET_CLASS, "exchange": _EXCHANGE}
                for s in symbols
            ]
        )
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[Instrument.symbol, Instrument.exchange]
        )
        await session.execute(stmt)
        await session.commit()

        result = await session.execute(
            select(Instrument.symbol, Instrument.id).where(
                Instrument.exchange == _EXCHANGE,
                Instrument.symbol.in_(symbols),
            )
        )
        return {symbol: instrument_id for symbol, instrument_id in result.all()}


async def run_ingest(
    *,
    connect_fn: Callable[[str], WSConnection] | None = None,
    exchange: SupportsFetchTickers | None = None,
) -> None:
    """Run the live crypto ingestion pipeline until cancelled.

    ``connect_fn`` and ``exchange`` are injectable for tests; the real ccxt /
    websockets clients are imported lazily and built only when they are None,
    so hermetic tests inject fakes and never import those libraries.
    """
    settings = get_settings()

    created_exchange = exchange is None
    exchange_obj: Any = exchange
    if exchange_obj is None:
        import ccxt.async_support as ccxt_async

        exchange_obj = ccxt_async.binance({"enableRateLimit": True})

    if connect_fn is None:
        import websockets

        def _default_connect(url: str) -> WSConnection:
            return cast(WSConnection, websockets.connect(url))

        connect_fn = _default_connect

    session_factory = get_sessionmaker()
    redis = get_redis()

    try:
        symbols = await get_top_n_by_volume(
            exchange_obj, settings.UNIVERSE_SIZE, settings.UNIVERSE_QUOTE_ASSET
        )
        symbol_to_instrument_id = await _ensure_instruments(session_factory, symbols)
        logger.info("ingest universe: %d symbols", len(symbol_to_instrument_id))

        buffer = CandleBuffer(symbol_to_instrument_id)
        consumer = BinanceWSConsumer(
            symbols=symbols,
            buffer=buffer,
            # redis<6 (pinned by arq) ships looser async stubs than the
            # SupportsRedisKV protocol; the client satisfies it at runtime.
            redis=cast(SupportsRedisKV, redis),
            connect_fn=connect_fn,
            max_backoff_s=settings.WS_MAX_BACKOFF_S,
            base_url=settings.BINANCE_WS_BASE_URL,
        )

        consumer_task = asyncio.create_task(consumer.run())
        flush_task = asyncio.create_task(buffer.run_flush_loop(session_factory))
        try:
            await asyncio.gather(consumer_task, flush_task)
        finally:
            for task in (consumer_task, flush_task):
                task.cancel()
            await asyncio.gather(consumer_task, flush_task, return_exceptions=True)
            # Drain anything buffered but not yet flushed so a shutdown does not
            # silently discard already-received closed candles.
            async with session_factory() as session:
                await buffer.flush(session)
                await session.commit()
    finally:
        if created_exchange:
            await exchange_obj.close()
