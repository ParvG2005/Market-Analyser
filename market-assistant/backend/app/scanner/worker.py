"""Rule engine worker: on candle close, evaluate enabled rules and fan out hits.

For each closed candle the worker warm-starts a fresh indicator cache from the
instrument's recent history (read via the SAME session as ``ctx["db"]`` so it
sees seeded/committed rows), computes an indicator snapshot including the new
bar, then evaluates every enabled ``ScanRule``. Rules that fire persist a
``ScanHit`` row and publish a JSON event to ``scan_hits:{user_id}`` for the
websocket fan-out. A Redis SET-NX dedup guard makes replay of the same
rule/instrument/timeframe/bar a no-op.

Key-format bridge: the Task-4 cache emits period-suffixed keys ("rsi:14"),
while the Task-5 evaluator looks up bare indicator names ("rsi"). The worker
strips the suffix before evaluating.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select

from app.ingest.nse_calendar import is_in_session
from app.models.instrument import Instrument
from app.models.scan_hit import ScanHit
from app.models.scan_rule import ScanRule
from app.scanner.cache import WARM_START_BARS, CandleLike, IndicatorCache, LoadHistory
from app.scanner.dedup import is_duplicate_hit
from app.scanner.dsl import parse_rule_definition
from app.scanner.evaluator import compile_rule
from app.scanner.history import load_recent_candles

# Period-suffixed keys the cache's recompute parser expects (it splits on ":"
# and int()-casts the period, so bare names would IndexError).
REQUESTED: list[str] = [
    "rsi:14",
    "ema:21",
    "sma:20",
    "vwap",
    "atr:14",
    "adx:14",
    "rel_volume:20",
    "gap_pct",
    "bollinger_mid:20:2.0",
    "bollinger_upper:20:2.0",
    "bollinger_lower:20:2.0",
]


class _CandleView:
    """Adapts a candle dict to the cache's positional OHLCV attribute contract."""

    def __init__(self, candle: dict[str, Any]) -> None:
        self.ts = candle["ts"]
        self.o = float(candle["o"])
        self.h = float(candle["h"])
        self.l = float(candle["l"])  # noqa: E741
        self.c = float(candle["c"])
        self.v = float(candle["v"])


def _json_safe(snapshot: dict[str, float]) -> dict[str, float | None]:
    # Postgres JSONB rejects NaN, and NaN is not valid JSON: map NaN -> None so
    # both the persisted payload and the published event serialize cleanly.
    return {
        k: (None if isinstance(v, float) and math.isnan(v) else v)
        for k, v in snapshot.items()
    }


async def on_candle_close(
    ctx: dict[str, Any], instrument_id: int, tf: str, candle: dict[str, Any]
) -> int:
    db = ctx["db"]
    redis = ctx["redis"]

    result = await db.execute(select(ScanRule).where(ScanRule.enabled.is_(True)))
    enabled_rules = list(result.scalars().all())
    if not enabled_rules:
        return 0

    # Market-hours guard: equity instruments must never be evaluated on a candle
    # whose close falls outside the NSE session (stale/off-hours data). Crypto
    # trades 24/7 and is unaffected; in-session equity passes through. Runs
    # after the enabled_rules early-return so a crypto/no-rules candle-close
    # never pays for an unnecessary Instrument fetch.
    instrument = await db.get(Instrument, instrument_id)
    if instrument is not None and instrument.asset_class == "equity":
        bar_ts = datetime.fromisoformat(str(candle["ts"]).replace("Z", "+00:00"))
        if not is_in_session(bar_ts):
            return 0

    # Warm-start async, then hand the sync cache a closure over the loaded rows.
    history = await load_recent_candles(db, instrument_id, tf, WARM_START_BARS)
    cache = IndicatorCache(
        load_history=cast(LoadHistory, lambda *_: history),
        requested_indicators=REQUESTED,
    )
    inst = cache.get_or_create(instrument_id, tf)
    snapshot = inst.update(cast(CandleLike, _CandleView(candle)))
    bare = {k.split(":")[0]: v for k, v in snapshot.items()}
    snapshot_by_tf = {tf: bare}

    safe_payload = _json_safe(snapshot)
    hit_ts = datetime.fromisoformat(str(candle["ts"]).replace("Z", "+00:00"))

    hits_written = 0
    for rule in enabled_rules:
        compiled = compile_rule(parse_rule_definition(rule.definition))
        if not any(t == tf for _, t in compiled.required_indicators()):
            continue
        if not compiled.evaluate(snapshot_by_tf):
            continue
        if await is_duplicate_hit(redis, rule.id, instrument_id, tf, str(candle["ts"])):
            continue

        hit = ScanHit(
            rule_id=rule.id,
            instrument_id=instrument_id,
            ts=hit_ts,
            payload=safe_payload,
        )
        db.add(hit)
        await db.commit()
        # expire_on_commit=False keeps the identity-mapped instance usable, but
        # the DB-assigned PK may not be loaded until refreshed; ensure hit.id.
        if hit.id is None:
            await db.refresh(hit)

        await redis.publish(
            f"scan_hits:{rule.user_id}",
            json.dumps(
                {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "instrument_id": instrument_id,
                    "tf": tf,
                    "ts": candle["ts"],
                    "payload": safe_payload,
                }
            ),
        )

        # Fan out Telegram alerts only when a live arq pool is present in ctx.
        # Scanner unit/integration tests pass ctx without a pool, so this stays
        # a no-op there; the live worker (app/worker.py) injects "arq_pool".
        pool = ctx.get("arq_pool")
        if pool is not None:
            await pool.enqueue_job("send_telegram_alert_job", hit.id)

        hits_written += 1

    return hits_written


async def scan_on_candle_close_job(
    ctx: dict[str, Any], instrument_id: int, tf: str, candle: dict[str, Any]
) -> int:
    """Thin live arq entrypoint. arq calls functions as ``func(ctx, *args)``.

    Opens a session from the live ``ctx["session_factory"]`` and adapts it to the
    ``ctx["db"]`` contract ``on_candle_close`` expects (which commits internally,
    so no outer commit is needed). Passes through the arq pool so hits fan out.
    """
    session_factory = ctx["session_factory"]
    async with session_factory() as session:
        sub_ctx: dict[str, Any] = {
            "db": session,
            "redis": ctx["redis"],
            "arq_pool": ctx.get("arq_pool"),
        }
        return await on_candle_close(sub_ctx, instrument_id, tf, candle)
