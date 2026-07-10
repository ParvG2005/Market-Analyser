import asyncio
import copy
import json
import sys
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.ingest import runner
from app.models.candle import CandleRow
from app.models.instrument import Instrument
from tests.fixtures.binance_klines import VALID_CLOSED_KLINE


def _kline(ts_ms: int) -> dict:
    msg = copy.deepcopy(VALID_CLOSED_KLINE)
    msg["k"]["t"] = ts_ms
    msg["k"]["T"] = ts_ms + 59999
    return msg


class _FakeWS:
    """Async CM + async iterator: yields the given messages, then cancels."""

    def __init__(self, messages: list[dict]) -> None:
        self._messages = messages

    async def __aenter__(self) -> "_FakeWS":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for m in self._messages:
            yield json.dumps(m)
        raise asyncio.CancelledError()


@pytest.mark.asyncio
async def test_run_ingest_wires_universe_instruments_and_candles(
    monkeypatch, session_factory
):
    # Fake exchange: two USDT pairs (kept, volume-sorted) + one non-USDT (dropped).
    exchange = AsyncMock()
    exchange.fetch_tickers = AsyncMock(
        return_value={
            "BTC/USDT": {"quoteVolume": 1000},
            "ETH/USDT": {"quoteVolume": 500},
            "DOGE/BTC": {"quoteVolume": 9999},
        }
    )

    # Two distinct closed klines for BTC/USDT (distinct ts -> two rows).
    kline1 = _kline(1700000000000)
    kline2 = _kline(1700000060000)

    def connect_fn(url: str) -> _FakeWS:
        return _FakeWS([kline1, kline2])

    # Bind the pipeline to the test's shared-connection factory + a fake redis
    # so it is fully hermetic (no real DB session pool, no real redis).
    monkeypatch.setattr(runner, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(runner, "get_redis", lambda: AsyncMock())

    modules_before = set(sys.modules)

    with pytest.raises(asyncio.CancelledError):
        await runner.run_ingest(connect_fn=connect_fn, exchange=exchange)

    # Lazy defaults were skipped because both args were injected.
    new_modules = set(sys.modules) - modules_before
    assert not any(m == "ccxt" or m.startswith("ccxt.") for m in new_modules)
    assert "websockets" not in new_modules

    # Universe selected -> Instrument rows created (get-or-create).
    async with session_factory() as session:
        symbols = set(
            (await session.execute(select(Instrument.symbol))).scalars().all()
        )
        candle_count = await session.scalar(
            select(func.count()).select_from(CandleRow)
        )
    assert symbols == {"BTC/USDT", "ETH/USDT"}
    # Parsed candles were buffered and the shutdown drain persisted them.
    assert candle_count == 2


@pytest.mark.asyncio
async def test_run_ingest_get_or_create_is_idempotent(monkeypatch, session_factory):
    exchange = AsyncMock()
    exchange.fetch_tickers = AsyncMock(
        return_value={"BTC/USDT": {"quoteVolume": 1000}}
    )

    def connect_fn(url: str) -> _FakeWS:
        return _FakeWS([])  # no candles, cancels immediately

    monkeypatch.setattr(runner, "get_sessionmaker", lambda: session_factory)
    monkeypatch.setattr(runner, "get_redis", lambda: AsyncMock())

    for _ in range(2):
        with pytest.raises(asyncio.CancelledError):
            await runner.run_ingest(connect_fn=connect_fn, exchange=exchange)

    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(Instrument)
            .where(Instrument.symbol == "BTC/USDT")
        )
    assert count == 1
