import pytest
from httpx import ASGITransport, AsyncClient

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
def app():
    return create_app()


@pytest.fixture
async def test_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
