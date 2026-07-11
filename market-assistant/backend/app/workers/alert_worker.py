"""Alert worker: fan out a scanner hit to every Telegram subscriber, rate-limited.

Enqueued by the scanner (``app/scanner/worker.py``) after each ``ScanHit`` insert.
Loads the hit and its rule/instrument, finds every ``AlertSubscription`` on that
rule with ``channel="telegram"``, and sends a formatted message per subscriber.
Sends are per-user fixed-window rate-limited; a user over their limit is skipped
(never crashes the job). If no bot token is configured the job is a no-op.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.alerts.telegram import format_hit_message, send_telegram_message
from app.core.config import get_settings
from app.core.deps import get_sessionmaker
from app.core.rate_limit import RateLimitExceeded, enforce_rate_limit
from app.models.alert_subscription import AlertSubscription
from app.models.instrument import Instrument
from app.models.scan_hit import ScanHit
from app.models.scan_rule import ScanRule


async def send_telegram_alert_job(ctx: dict[str, Any], hit_id: int) -> int:
    """Send a Telegram alert to every subscriber of the hit's rule.

    Returns the number of messages actually sent (skipping rate-limited users).
    """
    settings = get_settings()
    if not settings.telegram_bot_token:
        return 0

    session_factory = ctx.get("session_factory") or get_sessionmaker()
    redis = ctx["redis"]

    async with session_factory() as session:
        hit = await session.get(ScanHit, hit_id)
        if hit is None:
            return 0

        rule = await session.get(ScanRule, hit.rule_id)
        instrument = await session.get(Instrument, hit.instrument_id)
        if rule is None or instrument is None:
            return 0

        subs = (
            (
                await session.execute(
                    select(AlertSubscription).where(
                        AlertSubscription.rule_id == hit.rule_id,
                        AlertSubscription.channel == "telegram",
                    )
                )
            )
            .scalars()
            .all()
        )
        if not subs:
            return 0

        text = format_hit_message(
            {
                "symbol": instrument.symbol,
                "rule_name": rule.name,
                "ts": hit.ts,
                "payload": hit.payload,
            }
        )

    sent = 0
    for sub in subs:
        try:
            await enforce_rate_limit(
                redis,
                key=f"telegram_alert:{sub.user_id}",
                limit=settings.telegram_rate_limit_per_min,
                window_seconds=60,
            )
        except RateLimitExceeded:
            continue
        await send_telegram_message(settings.telegram_bot_token, sub.target, text)
        sent += 1

    return sent
