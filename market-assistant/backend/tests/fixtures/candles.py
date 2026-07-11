"""Deterministic synthetic OHLCV fixtures for backtest smoke tests.

Pure NumPy/pandas construction (dev deps). No randomness, no wall-clock:
every call returns byte-identical data so preset backtest stats are
reproducible. NEVER import pandas-ta here.
"""

import numpy as np
import pandas as pd

# 60 days of 15m bars = 5760 bars. Multi-week, multi-cycle, and fast enough
# that an O(n*window) preset walk-forward through run_backtest finishes in a
# couple of seconds. (Full 90d/8640 was trimmed for smoke-test speed.)
_BTC_15M_BARS = 5760
_BTC_15M_START = pd.Timestamp("2024-01-01", tz="UTC")


def _btc_15m_3mo() -> pd.DataFrame:
    n = _BTC_15M_BARS
    i = np.arange(n, dtype=float)

    base = 40_000.0
    drift = 1.5  # gentle net uptrend over the window
    # Two superimposed cycles give both trends and mean-reverting swings.
    amp1 = 2_500.0
    period1 = 96 * 7  # ~weekly swing
    amp2 = 900.0
    period2 = 96  # ~daily swing

    close = base + drift * i + amp1 * np.sin(i / period1) + amp2 * np.sin(i / period2)
    # Guaranteed positive by construction (base >> amp1+amp2), but be explicit.
    assert (close > 0).all()

    # Open = prior close (first bar opens at its own close).
    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1]

    wiggle = 0.0015 + 0.0010 * np.abs(np.sin(i / 53.0))
    hi = np.maximum(open_, close) * (1.0 + wiggle)
    lo = np.minimum(open_, close) * (1.0 - wiggle)

    base_vol = 100.0
    vol = base_vol * (1.0 + 0.5 * np.sin(i / 41.0))
    # Deterministic periodic spikes so rel_volume varies meaningfully.
    vol[(i.astype(int) % 97) == 0] *= 3.0

    idx = pd.date_range(_BTC_15M_START, periods=n, freq="15min")
    return pd.DataFrame(
        {"o": open_, "h": hi, "l": lo, "c": close, "v": vol},
        index=idx,
    )


def load_fixture_candles(name: str) -> pd.DataFrame:
    """Return a deterministic synthetic OHLCV DataFrame for ``name``.

    Columns ``o, h, l, c, v`` (floats), indexed by a 15-minute
    ``DatetimeIndex``. Unknown names raise ``ValueError``.
    """
    if name == "btc_15m_3mo":
        return _btc_15m_3mo()
    raise ValueError(f"unknown fixture name: {name!r}")
