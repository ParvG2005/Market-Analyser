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

    async def _take_batch(self) -> dict[str, list[Candle]]:
        # Atomically swap the pending batch out under the lock.
        async with self._lock:
            batch, self._pending = self._pending, defaultdict(list)
        return batch

    async def _requeue(self, batch: dict[str, list[Candle]]) -> None:
        # Merge a failed batch back into _pending under the lock so the next
        # tick retries it. Prepend the failed candles ahead of any that arrived
        # while the batch was in flight; the (instrument_id, tf, ts) upsert is
        # idempotent, so re-delivery of partially-written rows is safe.
        async with self._lock:
            for symbol, candles in batch.items():
                self._pending[symbol] = candles + self._pending[symbol]

    async def _write_batch(
        self, session: AsyncSession, batch: dict[str, list[Candle]]
    ) -> int:
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

    async def flush(self, session: AsyncSession) -> int:
        batch = await self._take_batch()
        return await self._write_batch(session, batch)

    async def run_flush_loop(
        self, session_factory: SessionFactory, interval_s: float = 5.0
    ) -> None:
        while True:
            await asyncio.sleep(interval_s)
            if self.pending_count == 0:
                continue
            batch = await self._take_batch()
            async with session_factory() as session:
                try:
                    written = await self._write_batch(session, batch)
                    await session.commit()
                    if written:
                        logger.info("buffer flush wrote %d candles", written)
                except Exception:
                    await session.rollback()
                    await self._requeue(batch)
                    logger.exception(
                        "buffer flush failed; re-queued %d candles for retry",
                        sum(len(v) for v in batch.values()),
                    )
