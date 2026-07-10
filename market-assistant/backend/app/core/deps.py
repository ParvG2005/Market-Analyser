from functools import lru_cache

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


@lru_cache
def get_redis() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)
