"""Phase 12 Task 5: global (all-users) daily LLM quota guard.

Protects the free-tier provider budget: a single Redis counter per provider per
UTC date is incremented on every LLM call; once the configured daily cap is hit,
``check_and_increment`` returns ``False`` (it never raises) so the orchestrator
can fall back gracefully instead of hammering the provider.

The app's Redis client is async (``redis.asyncio``), so the guard is async too.
"""

from __future__ import annotations

from datetime import date

import redis.asyncio as redis


def _today() -> date:
    return date.today()


# Slightly over 24h so a counter survives clock drift before its date rolls over.
_TTL_SECONDS = 60 * 60 * 26


class LlmQuotaGuard:
    def __init__(self, redis_client: redis.Redis, daily_quota: int):
        self._redis = redis_client
        self._daily_quota = daily_quota

    def _key(self, provider: str) -> str:
        return f"llm_quota:{provider}:{_today().isoformat()}"

    async def check_and_increment(self, provider: str) -> bool:
        key = self._key(provider)
        count = int(await self._redis.incr(key))
        if count == 1:
            await self._redis.expire(key, _TTL_SECONDS)
        return count <= self._daily_quota
