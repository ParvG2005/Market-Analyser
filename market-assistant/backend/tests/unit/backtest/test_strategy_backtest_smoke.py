"""Honest-path (`run_signal_backtest`) backtest smoke tests for strategy
presets. Each preset gets one case here; later Phase-6 tasks append theirs.
"""

import math

import app.strategies.breakout_retest  # noqa: F401 -- registers "breakout_retest"
import app.strategies.ema_vwap_trend  # noqa: F401 -- registers "ema_vwap_trend"
import app.strategies.orb  # noqa: F401 -- registers "orb" with the strategy registry
import app.strategies.vwap_revert  # noqa: F401 -- registers "vwap_revert"
from app.backtest.signal_bridge import run_signal_backtest
from app.strategies.registry import get_strategy
from tests.fixtures.candles import load_fixture_candles


def test_orb_backtest_smoke() -> None:
    strat = get_strategy("orb")
    result = run_signal_backtest(
        strat,
        load_fixture_candles("btc_15m_3mo"),
        strat.default_params(),
        fees_bps=10,
        slippage_bps=5,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0
    assert math.isfinite(result.stats["win_rate"])
    assert math.isfinite(result.stats["net_return"])


def test_ema_vwap_trend_backtest_smoke() -> None:
    # window=500 (vs the default 60): this preset's VWAP filter uses the
    # cumulative VWAP over the window it's handed, so it needs a longer
    # lookback context than the intraday presets (orb/vwap_revert) before a
    # cross's close lands on the trend side of VWAP. At window<=300 no cross
    # on this fixture clears the filter (legitimate selectivity, not a bug).
    strat = get_strategy("ema_vwap_trend")
    result = run_signal_backtest(
        strat,
        load_fixture_candles("btc_15m_3mo"),
        strat.default_params(),
        fees_bps=10,
        slippage_bps=5,
        window=500,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0


def test_vwap_revert_backtest_smoke() -> None:
    strat = get_strategy("vwap_revert")
    result = run_signal_backtest(
        strat,
        load_fixture_candles("btc_15m_3mo"),
        strat.default_params(),
        fees_bps=10,
        slippage_bps=5,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0


def test_breakout_retest_backtest_smoke() -> None:
    strat = get_strategy("breakout_retest")
    candles = load_fixture_candles("btc_15m_3mo")
    result = run_signal_backtest(
        strat,
        candles,
        strat.default_params(),
        fees_bps=10,
        slippage_bps=5,
        window=60,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0
