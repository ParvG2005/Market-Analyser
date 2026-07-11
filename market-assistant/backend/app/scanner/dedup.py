"""Same-bar hit dedup via a Redis SET NX key.

A rule/instrument/timeframe/bar tuple should produce at most one ``scan_hit``
even if the candle-close event is replayed (arq retry, duplicate publish). The
first writer atomically claims the key with ``SET key 1 NX EX``; any later
attempt for the same tuple sees the key already set and is treated as a
duplicate. The TTL is comfortably longer than the largest timeframe's same-bar
replay window, then expires so the key set stays bounded.
"""

from __future__ import annotations

from redis.asyncio import Redis

DEDUP_TTL_SECONDS = 6 * 3600


def dedup_key(rule_id: int, instrument_id: int, tf: str, bar_ts: str) -> str:
    return f"scan_hit_dedup:{rule_id}:{instrument_id}:{tf}:{bar_ts}"


async def is_duplicate_hit(
    redis: Redis, rule_id: int, instrument_id: int, tf: str, bar_ts: str
) -> bool:
    key = dedup_key(rule_id, instrument_id, tf, bar_ts)
    was_set = await redis.set(key, "1", nx=True, ex=DEDUP_TTL_SECONDS)
    return not was_set
