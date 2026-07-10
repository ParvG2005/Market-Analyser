import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.candle import Candle
from app.ingest.writer import upsert_candles

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class CandleBuffer:
    def __init__(self, symbol_to_instrument_id: dict[str, int]) -> None:
        self._symbol_to_instrument_id = symbol_to_instrument_id
        self._pending: dict[str, list[Candle]] = defaultdict(list)
        self._lock = asyncio.Lock()

    @property
    def pending_count(self) -> int:
        return sum(len(v) for v in self._pending.values())

    def add(self, candle: Candle) -> None:
        self._pending[candle.symbol].append(candle)

    async def flush(self, session: AsyncSession) -> int:
        async with self._lock:
            batch, self._pending = self._pending, defaultdict(list)

        total_written = 0
        for symbol, candles in batch.items():
            instrument_id = self._symbol_to_instrument_id.get(symbol)
            if instrument_id is None:
                logger.warning(
                    "flush: unknown symbol %s, dropping %d candles", symbol, len(candles)
                )
                continue
            total_written += await upsert_candles(session, instrument_id, candles)
        return total_written

    async def run_flush_loop(
        self, session_factory: SessionFactory, interval_s: float = 5.0
    ) -> None:
        while True:
            await asyncio.sleep(interval_s)
            if self.pending_count == 0:
                continue
            async with session_factory() as session:
                try:
                    written = await self.flush(session)
                    await session.commit()
                    if written:
                        logger.info("buffer flush wrote %d candles", written)
                except Exception:
                    await session.rollback()
                    logger.exception("buffer flush failed")
