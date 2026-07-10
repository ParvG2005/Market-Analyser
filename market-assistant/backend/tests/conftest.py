from datetime import UTC, datetime, timedelta

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
