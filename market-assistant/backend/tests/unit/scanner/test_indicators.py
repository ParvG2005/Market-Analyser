import math

import numpy as np
import pandas as pd
import pandas_ta as ta
import pytest

from app.scanner.indicators import adx, atr, bollinger, ema, gap_pct, rel_volume, rsi, sma, vwap


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


def test_atr_matches_pandas_ta():
    df = _synthetic_ohlcv()
    expected = ta.atr(df["high"], df["low"], df["close"], length=14)
    result = atr(df["high"].tolist(), df["low"].tolist(), df["close"].tolist(), period=14)
    for i in range(20, len(df)):
        assert result[i] == pytest.approx(expected[i], rel=1e-3)


def test_adx_matches_pandas_ta():
    df = _synthetic_ohlcv(n=200)
    expected = ta.adx(df["high"], df["low"], df["close"], length=14)["ADX_14"]
    result = adx(df["high"].tolist(), df["low"].tolist(), df["close"].tolist(), period=14)
    for i in range(40, len(df)):
        if not math.isnan(expected[i]):
            assert result[i] == pytest.approx(expected[i], rel=1e-2)


def test_rel_volume_is_ratio_to_rolling_average():
    volumes = [10.0] * 20 + [50.0]
    result = rel_volume(volumes, period=20)
    assert result[20] == pytest.approx(5.0, rel=1e-9)


def test_gap_pct_computes_open_vs_prior_close():
    opens = [102.0, 95.0]
    prev_closes = [100.0, 100.0]
    result = gap_pct(opens, prev_closes)
    assert result[0] == pytest.approx(2.0, rel=1e-9)
    assert result[1] == pytest.approx(-5.0, rel=1e-9)


def test_bollinger_matches_pandas_ta():
    df = _synthetic_ohlcv()
    expected = ta.bbands(df["close"], length=20, std=2.0)
    mid, upper, lower = bollinger(df["close"].tolist(), period=20, std_mult=2.0)
    for i in range(19, len(df)):
        assert mid[i] == pytest.approx(expected["BBM_20_2.0_2.0"][i], rel=1e-6)
        assert upper[i] == pytest.approx(expected["BBU_20_2.0_2.0"][i], rel=1e-6)
        assert lower[i] == pytest.approx(expected["BBL_20_2.0_2.0"][i], rel=1e-6)
