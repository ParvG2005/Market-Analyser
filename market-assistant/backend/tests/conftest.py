import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_engine, get_redis
from app.main import create_app


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
async def db_session():
    # Test isolation via the "join an external transaction" pattern: open an
    # outer connection-level transaction, bind the session to that connection
    # with join_transaction_mode="create_savepoint" so the session's own
    # commit()/rollback() act on a SAVEPOINT rather than the outer transaction.
    # Tearing down rolls the outer transaction back, so nothing the test
    # committed persists. Setup happens after the autouse _reset_cached_engine
    # fixture, so this connection/session is closed before that disposes the
    # engine.
    engine = get_engine()
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def test_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
