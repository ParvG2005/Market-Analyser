"""Shared reference-level helpers used by every strategy preset.

Pure arithmetic (`rr_target`) plus thin pandas lookups over the candle
DataFrame (`swing_low`/`swing_high`) that presets use to derive entry/stop/
target levels.
"""

from __future__ import annotations

import pandas as pd


def rr_target(entry: float, stop: float, direction: str, rr: float) -> float:
    """Risk-reward target price given an entry, stop, direction, and R multiple."""
    risk = abs(entry - stop)
    return entry + risk * rr if direction == "long" else entry - risk * rr


def candle_ts(candles: pd.DataFrame, i: int) -> pd.Timestamp:
    """Per-bar timestamp: prefer a `ts` column (unit-test fixtures), else the
    DataFrame's DatetimeIndex (backtest fixtures/bridge)."""
    if "ts" in candles.columns:
        return pd.Timestamp(candles["ts"].iloc[i])
    return pd.Timestamp(candles.index[i])


def swing_low(candles: pd.DataFrame, lookback: int) -> float:
    """Lowest low over the trailing `lookback` bars."""
    return float(candles["l"].iloc[-lookback:].min())


def swing_high(candles: pd.DataFrame, lookback: int) -> float:
    """Highest high over the trailing `lookback` bars."""
    return float(candles["h"].iloc[-lookback:].max())
