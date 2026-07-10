from collections.abc import AsyncIterator
from functools import lru_cache
from typing import cast

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    # NOT lru_cache'd: the autouse test fixture disposes get_engine() and clears
    # its cache after every test, so a cached sessionmaker would stay bound to a
    # disposed engine / dead event loop (asyncpg cross-event-loop failure).
    # Construction is trivial, so rebuild on the current engine each call.
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession.

    Tests override this to bind sessions to their shared transaction; see
    the candles integration tests.
    """
    async with get_sessionmaker()() as session:
        yield session


@lru_cache
def get_redis() -> redis.Redis:
    # redis<6 (pinned transitively by arq) ships an untyped from_url; cast the
    # result back to the annotated return type to keep mypy --strict green.
    client = redis.from_url(  # type: ignore[no-untyped-call]
        get_settings().redis_url, decode_responses=True
    )
    return cast(redis.Redis, client)
