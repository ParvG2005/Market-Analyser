import uuid
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
import redis as redis_sync
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from app.core.config import get_settings
from app.core.deps import get_engine, get_redis, get_session
from app.main import create_app
from app.models.candle import CandleRow
from app.models.instrument import Instrument
from app.scanner.worker import on_candle_close


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_schema():
    # A freshly-started Postgres (local dev or CI) has an empty `public`
    # schema. Acceptance and ingest integration tests INSERT into tables
    # (instruments/candles/news_items/...) that only exist after migrations,
    # and pytest may collect them before tests/integration/test_migrations.py
    # creates the schema, so run `alembic upgrade head` ONCE at session start.
    # This is synchronous (command.upgrade manages its own event loop, see
    # alembic/env.py), so it does not conflict with the function-scoped
    # event loops pytest-asyncio hands each test. test_migrations.py may later
    # drop and re-create the schema mid-session; nothing table-dependent is
    # collected after it, so that is safe.
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
async def _reset_cached_engine():
    # get_engine()/get_redis() are lru_cache'd, but pytest-asyncio gives each
    # test its own event loop by default. asyncpg/redis connections can't
    # cross event loops, so the cached clients must be disposed and evicted
    # after every test.
    yield
    engine = get_engine()
    await engine.dispose()
    get_engine.cache_clear()

    redis_client = get_redis()
    await redis_client.aclose()
    get_redis.cache_clear()


@pytest.fixture
async def db_connection():
    # Test isolation via the "join an external transaction" pattern: open an
    # outer connection-level transaction shared by every session in a test.
    # Sessions bound to this connection with join_transaction_mode=
    # "create_savepoint" act on a SAVEPOINT for their own commit()/rollback(),
    # so the outer transaction stays open and all sessions see each other's
    # (savepoint-committed) writes. Tearing down rolls the outer transaction
    # back, so nothing a test committed persists. Setup happens after the
    # autouse _reset_cached_engine fixture, so this connection is closed before
    # that disposes the engine.
    engine = get_engine()
    connection = await engine.connect()
    transaction = await connection.begin()
    try:
        yield connection
    finally:
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()


@pytest.fixture
async def db_session(db_connection):
    session = AsyncSession(
        bind=db_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
def session_factory(db_connection):
    # Zero-arg callable yielding a NEW AsyncSession bound to the SAME shared
    # connection/outer transaction as db_session. Used as `async with
    # session_factory() as s`; a session's commit() releases a savepoint (the
    # outer transaction survives) so its writes are visible to db_session and
    # to later factory sessions. The outer rollback in db_connection cleans up.
    def _make() -> AsyncSession:
        return AsyncSession(
            bind=db_connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

    return _make


@pytest.fixture
def test_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def auth_headers(test_user_id: uuid.UUID) -> dict[str, str]:
    return {"X-Dev-User": str(test_user_id)}


@pytest.fixture
def other_user_headers(other_user_id: uuid.UUID) -> dict[str, str]:
    return {"X-Dev-User": str(other_user_id)}


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def test_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def client(app, db_connection, session_factory):
    # Like test_client, but the get_session dependency is bound to the SAME
    # shared connection/outer transaction as db_session, so the API reads
    # rows a test seeded (and savepoint-committed) via db_session.
    async def _override_get_session():
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def redis_sync_client():
    # Plain synchronous Redis client against the same instance the app uses,
    # for test-side publishing into the pub/sub fan-out. Skips the test when
    # no Redis is reachable (e.g. a bare unit-only environment).
    client = redis_sync.Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        client.ping()
    except Exception:
        pytest.skip("Redis not available")
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
async def redis_client():
    # Async Redis client (decode_responses=True) against the app's instance,
    # for the scanner worker's pub/sub fan-out and dedup keys. Skips when Redis
    # is unreachable. Do NOT aclose/cache_clear here: the autouse
    # _reset_cached_engine fixture already disposes get_redis after the test;
    # a double-close would error.
    client = get_redis()
    try:
        await client.ping()
    except Exception:
        pytest.skip("Redis not available")

    # The suite shares this Redis instance across runs, but Postgres FK id
    # sequences reset whenever the schema is recreated (see
    # test_migrations.py), so a fresh rule_id/instrument_id combined with a
    # fixed test candle ts can collide with a leftover
    # scan_hit_dedup:{rule_id}:{instrument_id}:{tf}:{bar_ts} key from a
    # previous run and wrongly suppress a hit. Clear only the scanner dedup
    # keyspace (never flushdb - other tests/data may share this instance) so
    # every run starts hermetic.
    keys = [k async for k in client.scan_iter(match="scan_hit_dedup:*")]
    if keys:
        await client.delete(*keys)

    yield client


@pytest.fixture
async def sample_instrument(db_session):
    instrument = Instrument(
        symbol="BTC/USDT", asset_class="crypto", exchange="binance", active=True
    )
    db_session.add(instrument)
    await db_session.flush()
    return instrument


@pytest.fixture
async def seed_btc_1m_candles(db_session):
    instrument = Instrument(
        symbol="BTC/USDT", asset_class="crypto", exchange="binance", active=True
    )
    db_session.add(instrument)
    await db_session.flush()

    start = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(60):
        db_session.add(
            CandleRow(
                instrument_id=instrument.id,
                tf="1m",
                ts=start + timedelta(minutes=i),
                o=100 + i,
                h=101 + i,
                l=99 + i,
                c=100.5 + i,
                v=10 + i,
            )
        )
    await db_session.commit()
    return instrument


def _rsi_dip_with_volume_spike_series() -> tuple[list[float], list[float]]:
    # Matches Task 5's golden series: 40 flat bars, then a 15-bar monotonic
    # RSI-triggering drop; a single relative-volume spike at bar index 50.
    # By bar 50 the close series has fallen monotonically (RSI -> ~0, < 30) and
    # rel_volume(20) = 200 / 20-baseline = 10 (> 2), so the AND rule fires there.
    closes = [100.0] * 40 + list(np.linspace(100, 70, 15))
    volumes = [20.0] * 55
    volumes[50] = 200.0
    return closes, volumes


@pytest.fixture
async def replay_synthetic_candles(db_session, redis_client):
    """Replay a synthetic candle series through the production candle-close path.

    CRITICAL: ``on_candle_close`` builds a FRESH ``IndicatorCache`` on every call
    and warm-starts it by loading candle history FROM THE DB (via ``ctx["db"]``),
    then appends only the one passed candle. So a bar only has enough history to
    make rsi/rel_volume non-NaN if the PRIOR bars are already persisted. We
    therefore PROCESS bar i against persisted history 0..i-1, THEN persist bar i
    on the SAME session (SAVEPOINT-isolated, so a separate connection wouldn't
    see the flushed rows) so the NEXT bar's warm-start can read it.
    """

    async def _replay(instrument_id: int, tf: str, scenario: str) -> None:
        if scenario != "rsi_dip_with_volume_spike":
            raise ValueError(f"unknown scenario {scenario!r}")
        closes, volumes = _rsi_dip_with_volume_spike_series()
        for i, (c, v) in enumerate(zip(closes, volumes, strict=True)):
            ts = f"2026-01-01T00:{i:02d}:00Z"
            candle = {
                "ts": ts,
                "o": c - 0.1,
                "h": c + 0.5,
                "l": c - 0.5,
                "c": c,
                "v": v,
            }
            # 1) process bar i against history 0..i-1 (a hit may fire here)
            await on_candle_close(
                {"db": db_session, "redis": redis_client},
                instrument_id=instrument_id,
                tf=tf,
                candle=candle,
            )
            # 2) persist bar i so the next bar's warm-start sees it
            db_session.add(
                CandleRow(
                    instrument_id=instrument_id,
                    tf=tf,
                    ts=datetime.fromisoformat(ts.replace("Z", "+00:00")),
                    o=c - 0.1,
                    h=c + 0.5,
                    l=c - 0.5,
                    c=c,
                    v=v,
                )
            )
            await db_session.flush()

    return _replay


@pytest.fixture
def fixture_trending_candles() -> pd.DataFrame:
    """Synthetic 60-bar monotonically-rising OHLCV series (deterministic,
    arithmetic-only) engineered so the repo's real `adx()` yields a strongly
    trending last value (verified empirically: last ADX == 100.0, well above
    any `min_adx_trend` threshold used in tests).

    A clean, noise-free linear uptrend maximizes +DI relative to -DI (down
    moves never occur), so ADX saturates at 100 — deliberately steep/clean
    rather than a realistic price series, to make the gate's trend/range
    branches unambiguous in tests.
    """
    n = 60
    closes = [100.0 + i * 2.0 for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    opens = [c - 1.5 for c in closes]
    volumes = [1_000.0] * n
    return pd.DataFrame({"o": opens, "h": highs, "l": lows, "c": closes, "v": volumes})
