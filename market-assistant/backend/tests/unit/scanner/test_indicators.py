import numpy as np
import pandas as pd
import pandas_ta as ta
import pytest

from app.scanner.indicators import ema, rsi, sma, vwap


def _synthetic_ohlcv(n=100, seed=42):
    rng = np.random.default_rng(seed)
    closes = 100 + np.cumsum(rng.normal(0, 1, n))
    highs = closes + rng.uniform(0, 1, n)
    lows = closes - rng.uniform(0, 1, n)
    opens = closes + rng.uniform(-0.5, 0.5, n)
    volumes = rng.uniform(10, 100, n)
    # A DatetimeIndex (all within one session) is required by the installed
    # pandas-ta version's vwap() for session-anchored cumulative grouping;
    # unrelated indicators (sma/ema/rsi) ignore the index.
    index = pd.date_range("2024-01-02 09:30", periods=n, freq="min")
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=index,
    )


def test_sma_matches_pandas_ta():
    df = _synthetic_ohlcv()
    expected = ta.sma(df["close"], length=20)
    result = sma(df["close"].tolist(), period=20)
    for i in range(19, len(df)):
        assert result[i] == pytest.approx(expected.iloc[i], rel=1e-9)


def test_ema_matches_pandas_ta():
    df = _synthetic_ohlcv()
    expected = ta.ema(df["close"], length=12)
    result = ema(df["close"].tolist(), period=12)
    for i in range(11, len(df)):
        assert result[i] == pytest.approx(expected.iloc[i], rel=1e-6)


def test_rsi_matches_pandas_ta():
    df = _synthetic_ohlcv()
    expected = ta.rsi(df["close"], length=14)
    result = rsi(df["close"].tolist(), period=14)
    for i in range(27, len(df)):  # RSI needs warmup for Wilder smoothing to converge
        assert result[i] == pytest.approx(expected.iloc[i], rel=1e-6)


def test_vwap_matches_pandas_ta_single_session():
    df = _synthetic_ohlcv(n=50)
    expected = ta.vwap(df["high"], df["low"], df["close"], df["volume"])
    result = vwap(
        df["high"].tolist(), df["low"].tolist(), df["close"].tolist(), df["volume"].tolist()
    )
    for i in range(len(df)):
        assert result[i] == pytest.approx(expected.iloc[i], rel=1e-9)
