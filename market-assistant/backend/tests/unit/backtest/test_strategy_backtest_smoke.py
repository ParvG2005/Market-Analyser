"""Honest-path (`run_signal_backtest`) backtest smoke tests for strategy
presets. Each preset gets one case here; later Phase-6 tasks append theirs.
"""

import math

import app.strategies.orb  # noqa: F401 -- registers "orb" with the strategy registry
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
