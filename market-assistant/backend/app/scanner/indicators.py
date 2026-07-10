"""Core technical indicators over plain Python float lists.

Pure-Python and stateless: no pandas/numpy dependency at runtime. Values are
cross-checked in tests against `pandas-ta` fixtures (a dev-only dependency).
Used by the scanner's batch warm-start cache and cross-checked against
incremental updates.
"""

from __future__ import annotations

NAN = float("nan")


def sma(values: list[float], period: int) -> list[float]:
    """Simple moving average over a trailing window of `period` values."""
    out = [NAN] * len(values)
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def ema(values: list[float], period: int) -> list[float]:
    """Exponential moving average, seeded with an SMA over the first `period` values."""
    out = [NAN] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(closes: list[float], period: int = 14) -> list[float]:
    """Relative Strength Index using Wilder's smoothing (RMA).

    Matches `pandas_ta.rsi`'s default `mamode="rma"`: gains/losses are
    smoothed with an EWM of alpha=1/period seeded from the *first* delta
    (pandas `ewm(adjust=False)` semantics), not an SMA warm-up over the
    first `period` bars. RSI values are therefore defined from index 1
    onward rather than only after a full `period` warm-up window.
    """
    out = [NAN] * len(closes)
    if len(closes) <= period:
        return out
    alpha = 1 / period
    avg_gain: float | None = None
    avg_loss: float | None = None
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        if avg_gain is None or avg_loss is None:
            avg_gain = gain
            avg_loss = loss
        else:
            avg_gain = alpha * gain + (1 - alpha) * avg_gain
            avg_loss = alpha * loss + (1 - alpha) * avg_loss
        out[i] = _rsi_from_avgs(avg_gain, avg_loss)
    return out


def _rsi_from_avgs(avg_gain: float, avg_loss: float) -> float:
    denom = avg_gain + avg_loss
    if denom == 0:
        return NAN
    return 100 * avg_gain / denom


def vwap(
    highs: list[float], lows: list[float], closes: list[float], volumes: list[float]
) -> list[float]:
    """Volume-weighted average price, cumulative over the given bars.

    Callers are responsible for session resets: pass only one trading
    session's bars per call (e.g. one day) to match daily VWAP semantics.
    """
    out = [NAN] * len(closes)
    cum_pv = 0.0
    cum_v = 0.0
    for i in range(len(closes)):
        typical = (highs[i] + lows[i] + closes[i]) / 3
        cum_pv += typical * volumes[i]
        cum_v += volumes[i]
        out[i] = cum_pv / cum_v if cum_v else NAN
    return out
