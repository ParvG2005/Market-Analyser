"""Per-user fixed-window chat rate limiting via Redis."""

from __future__ import annotations

from app.core.config import get_settings


async def check_rate_limit(
    user_id: str,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> bool:
    """Return True if the user is under the cap, False if they've exceeded it.

    Fail-open: if Redis is unreachable, allow the request rather than block chat.
    """
    from app.core.deps import get_redis

    settings = get_settings()
    limit = settings.CHAT_RATE_LIMIT if limit is None else limit
    window_seconds = settings.CHAT_RATE_WINDOW_SECONDS if window_seconds is None else window_seconds

    key = f"chat_rate_limit:{user_id}"
    try:
        redis = get_redis()
        count = await redis.incr(key)
        # H6: EXPIRE NX on every call keeps the window fixed and self-heals a
        # counter left TTL-less by a crash between INCR and EXPIRE.
        await redis.expire(key, window_seconds, nx=True)
    except Exception:
        return True
    return bool(count <= limit)
