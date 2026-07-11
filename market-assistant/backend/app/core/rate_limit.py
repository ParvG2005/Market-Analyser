from __future__ import annotations

import redis.asyncio as redis


class RateLimitExceeded(Exception):
    def __init__(self, key: str, limit: int, window_seconds: int) -> None:
        self.key = key
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(f"Rate limit exceeded for {key}: {limit}/{window_seconds}s")


async def check_rate_limit(
    client: redis.Redis, key: str, limit: int, window_seconds: int
) -> bool:
    """Fixed-window counter. Increments ratelimit:{key}, expiring the counter
    after window_seconds on first hit. Returns True if allowed (count <= limit),
    False if over the limit."""
    redis_key = f"ratelimit:{key}"
    count = await client.incr(redis_key)
    if count == 1:
        await client.expire(redis_key, window_seconds)
    return bool(count <= limit)


async def enforce_rate_limit(
    client: redis.Redis, key: str, limit: int, window_seconds: int
) -> None:
    if not await check_rate_limit(client, key, limit, window_seconds):
        raise RateLimitExceeded(key, limit, window_seconds)
