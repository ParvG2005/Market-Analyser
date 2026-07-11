"""Signal worker: candle-close -> gated preset evaluation -> signals + WS publish.

On each closed candle the worker opens its own DB session, loads every enabled
``StrategyConfig`` for the (instrument, tf), pulls recent candle history, and for
each config runs the registered preset behind two gates (asset-class filter and
the ADX regime gate). Every emitted ``SignalCandidate`` is persisted as a
``Signal`` row and published to the ``signals:{symbol}:{tf}`` Redis channel with
the same JSON shape as ``SignalOut`` (consumed by the WS relay / frontend).

Presets self-register on import, so we import the package's preset modules here
to guarantee the registry is populated when the worker runs standalone (arq).
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import select

from app.core.deps import get_redis, get_sessionmaker
from app.models.instrument import Instrument
from app.models.signal import Signal
from app.models.strategy_config import StrategyConfig
from app.scanner.history import load_recent_candles
from app.strategies import (  # noqa: F401  (imported for registry side effects)
    bb_rsi_revert,
    breakout_retest,
    ema_vwap_trend,
    funding_extreme,
    grid_range,
    orb,
    pullback_trend,
    vwap_revert,
)
from app.strategies.regime_gate import adx_allows
from app.strategies.registry import get_strategy

# ema_vwap_trend's cumulative-VWAP filter only admits trades after ~500 bars, so
# we load 500 candles to keep live signal generation aligned with the backtest.
_HISTORY_BARS = 500


def _f(value: Any) -> float:
    """Coerce a candle OHLCV cell (Decimal, never None in practice) to float."""
    return float(value)


def _json_safe(value: Any) -> Any:
    """Map NaN floats to None so JSON.dumps and JSONB both serialize cleanly."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


async def on_candle_close(instrument_id: int, tf: str) -> None:
    async with get_sessionmaker()() as session:
        instrument = await session.get(Instrument, instrument_id)
        if instrument is None:
            return

        configs = (
            await session.execute(
                select(StrategyConfig).where(
                    StrategyConfig.instrument_id == instrument_id,
                    StrategyConfig.tf == tf,
                    StrategyConfig.enabled.is_(True),
                )
            )
        ).scalars().all()
        if not configs:
            return

        rows = await load_recent_candles(session, instrument_id, tf, limit=_HISTORY_BARS)
        df = pd.DataFrame(
            [
                {
                    "ts": r.ts,
                    "o": _f(r.o),
                    "h": _f(r.h),
                    "l": _f(r.l),
                    "c": _f(r.c),
                    "v": _f(r.v),
                }
                for r in rows
            ]
        )

        redis = get_redis()

        for cfg in configs:
            try:
                strategy = get_strategy(cfg.strategy)
            except KeyError:
                continue

            filter_asset = getattr(strategy, "asset_class_filter", None)
            if filter_asset not in (None, instrument.asset_class):
                continue
            if not adx_allows(df, mode=strategy.regime_mode):
                continue

            for candidate in strategy.generate_signals(df, cfg.params):
                ts = candidate.ts
                py_ts: datetime = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                if py_ts.tzinfo is None:
                    py_ts = py_ts.replace(tzinfo=UTC)

                meta = _json_safe(candidate.meta)
                signal = Signal(
                    instrument_id=instrument_id,
                    strategy=cfg.strategy,
                    direction=candidate.direction,
                    ts=py_ts,
                    confidence=_json_safe(candidate.confidence),
                    ref_entry=_json_safe(candidate.ref_entry),
                    ref_sl=_json_safe(candidate.ref_sl),
                    ref_tp=_json_safe(candidate.ref_tp),
                    meta=meta,
                )
                session.add(signal)
                await session.flush()

                payload = {
                    "id": signal.id,
                    "instrument_id": instrument_id,
                    "strategy": cfg.strategy,
                    "direction": candidate.direction,
                    "ts": py_ts.isoformat(),
                    "confidence": _json_safe(candidate.confidence),
                    "ref_entry": _json_safe(candidate.ref_entry),
                    "ref_sl": _json_safe(candidate.ref_sl),
                    "ref_tp": _json_safe(candidate.ref_tp),
                    "backtest_ref": None,
                    "meta": meta,
                }
                await redis.publish(
                    f"signals:{instrument.symbol}:{tf}", json.dumps(payload)
                )

        await session.commit()


async def on_candle_close_job(ctx: dict[str, Any], instrument_id: int, tf: str) -> None:
    """Thin arq entrypoint. arq calls functions as ``func(ctx, *args)``."""
    await on_candle_close(instrument_id, tf)
