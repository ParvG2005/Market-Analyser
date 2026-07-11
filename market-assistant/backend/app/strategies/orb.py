"""Opening Range Breakout (ORB) preset.

Defines an "opening range" from the first `or_bars` bars of the candles
handed to `generate_signals` and fires a long/short signal on the first
subsequent bar that closes outside that range on confirming relative
volume (`app.scanner.indicators.rel_volume`).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.scanner.indicators import rel_volume
from app.strategies.base import SignalCandidate
from app.strategies.levels import candle_ts, rr_target
from app.strategies.registry import register


class ORBStrategy:
    name = "orb"
    regime_mode = "trend"

    def param_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "or_bars": {"type": "integer", "minimum": 1, "default": 4},
                "rr": {"type": "number", "minimum": 0.5, "default": 2.0},
                "min_rel_volume": {"type": "number", "minimum": 1.0, "default": 2.0},
            },
            "required": ["or_bars", "rr", "min_rel_volume"],
        }

    def default_params(self) -> dict[str, Any]:
        return {"or_bars": 4, "rr": 2.0, "min_rel_volume": 2.0}

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        or_bars = params["or_bars"]
        rr = params["rr"]
        min_rel_vol = params["min_rel_volume"]

        if len(candles) <= or_bars:
            return []

        opening_range = candles.iloc[:or_bars]
        or_high = float(opening_range["h"].max())
        or_low = float(opening_range["l"].min())

        rv = rel_volume(candles["v"].astype(float).tolist(), period=or_bars)
        signals: list[SignalCandidate] = []

        for i in range(or_bars, len(candles)):
            bar = candles.iloc[i]
            bar_rel_vol = rv[i]
            if bar_rel_vol != bar_rel_vol:  # NaN check without importing math
                continue
            if bar["c"] > or_high and bar_rel_vol >= min_rel_vol:
                entry = float(bar["c"])
                signals.append(
                    SignalCandidate(
                        ts=candle_ts(candles, i),
                        direction="long",
                        ref_entry=entry,
                        ref_sl=or_low,
                        ref_tp=rr_target(entry, or_low, "long", rr),
                        meta={"or_high": or_high, "or_low": or_low, "rel_volume": bar_rel_vol},
                    )
                )
                break
            if bar["c"] < or_low and bar_rel_vol >= min_rel_vol:
                entry = float(bar["c"])
                signals.append(
                    SignalCandidate(
                        ts=candle_ts(candles, i),
                        direction="short",
                        ref_entry=entry,
                        ref_sl=or_high,
                        ref_tp=rr_target(entry, or_high, "short", rr),
                        meta={"or_high": or_high, "or_low": or_low, "rel_volume": bar_rel_vol},
                    )
                )
                break

        return signals


register(ORBStrategy())
