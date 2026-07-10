import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_engine
from app.main import create_app


@pytest.fixture(autouse=True)
async def _reset_cached_engine():
    # get_engine() is lru_cache'd, but pytest-asyncio gives each test its own
    # event loop by default. asyncpg connections can't cross event loops, so
    # the cached engine/pool must be disposed and evicted after every test.
    yield
    engine = get_engine()
    await engine.dispose()
    get_engine.cache_clear()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def test_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
