import math
from typing import Any

import pandas as pd
import pytest

from app.backtest.runner import run_backtest
from app.backtest.signal_bridge import SignalStrategyAdapter
from app.strategies.base import SignalCandidate
from tests.fixtures.candles import load_fixture_candles


class _FakePreset:
    """Fires exactly one SignalCandidate when the trailing window's last
    bar timestamp matches ``fire_ts``. Mimics a Phase-6 preset."""

    def __init__(
        self,
        fire_ts: pd.Timestamp,
        direction: str,
        ref_entry: float,
        ref_sl: float,
        ref_tp: float,
    ) -> None:
        self.name = "fake"
        self._fire_ts = fire_ts
        self._direction = direction
        self._ref_entry = ref_entry
        self._ref_sl = ref_sl
        self._ref_tp = ref_tp

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]:
        last_ts = candles.index[-1]
        if last_ts != self._fire_ts:
            return []
        return [
            SignalCandidate(
                ts=last_ts,
                direction=self._direction,
                ref_entry=self._ref_entry,
                ref_sl=self._ref_sl,
                ref_tp=self._ref_tp,
            )
        ]


def _candles(rows: list[dict[str, float]]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="15min", tz="UTC")
    return pd.DataFrame(rows, index=idx)


def test_long_tp_win():
    # Entry at bar 2 (c=100); TP=105 touched at bar 4; SL=95 never touched first.
    rows = [
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},  # 0
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},  # 1
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},  # 2 entry
        {"o": 100, "h": 103, "l": 98, "c": 101, "v": 1.0},  # 3 no touch
        {"o": 101, "h": 106, "l": 100, "c": 106, "v": 1.0},  # 4 TP win
        {"o": 106, "h": 106, "l": 106, "c": 106, "v": 1.0},  # 5
    ]
    candles = _candles(rows)
    fire_ts = candles.index[2]
    preset = _FakePreset(fire_ts, "long", ref_entry=100, ref_sl=95, ref_tp=105)
    adapter = SignalStrategyAdapter(preset, window=10)

    sig = adapter.generate_signals(candles, {})
    assert list(sig["entries"]) == [False, False, True, False, False, False]
    assert list(sig["exits"]) == [False, False, False, False, True, False]

    result = run_backtest(adapter, candles, {}, fees_bps=10.0, slippage_bps=5.0)
    assert result.stats["trade_count"] == 1
    assert result.trades[0].net_pnl > 0
    assert result.stats["win_rate"] == 1.0


def test_both_touch_same_bar_resolves_as_sl_loss():
    # Entry at bar 2 (c=100); bar 3 touches BOTH TP(105) and SL(95) -> SL loss.
    rows = [
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},  # 0
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},  # 1
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},  # 2 entry
        {"o": 100, "h": 106, "l": 94, "c": 95, "v": 1.0},  # 3 both touch -> SL
        {"o": 95, "h": 95, "l": 95, "c": 95, "v": 1.0},  # 4
    ]
    candles = _candles(rows)
    fire_ts = candles.index[2]
    preset = _FakePreset(fire_ts, "long", ref_entry=100, ref_sl=95, ref_tp=105)
    adapter = SignalStrategyAdapter(preset, window=10)

    sig = adapter.generate_signals(candles, {})
    assert list(sig["entries"]) == [False, False, True, False, False]
    assert list(sig["exits"]) == [False, False, False, True, False]

    result = run_backtest(adapter, candles, {}, fees_bps=10.0, slippage_bps=5.0)
    assert result.stats["trade_count"] == 1
    assert result.trades[0].net_pnl < 0
    assert result.stats["win_rate"] == 0.0


def test_short_tp_exit_bar():
    # Short entry at bar 2 (c=100); TP=95 (low<=95) touched at bar 3; SL=105 above.
    rows = [
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},  # 0
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},  # 1
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},  # 2 entry
        {"o": 100, "h": 101, "l": 94, "c": 95, "v": 1.0},  # 3 TP (short) touch
        {"o": 95, "h": 95, "l": 95, "c": 95, "v": 1.0},  # 4
    ]
    candles = _candles(rows)
    fire_ts = candles.index[2]
    preset = _FakePreset(fire_ts, "short", ref_entry=100, ref_sl=105, ref_tp=95)
    adapter = SignalStrategyAdapter(preset, window=10)

    sig = adapter.generate_signals(candles, {})
    assert list(sig["entries"]) == [False, False, True, False, False]
    assert list(sig["exits"]) == [False, False, False, True, False]

    result = run_backtest(adapter, candles, {}, fees_bps=10.0, slippage_bps=5.0)
    assert result.stats["trade_count"] == 1


def test_ts_column_candles_supported():
    # Same as long-win but candles carry ts as a COLUMN, not an index.
    rows = [
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},
        {"o": 100, "h": 100, "l": 100, "c": 100, "v": 1.0},
        {"o": 100, "h": 103, "l": 98, "c": 101, "v": 1.0},
        {"o": 101, "h": 106, "l": 100, "c": 106, "v": 1.0},
    ]
    ts = pd.date_range("2024-01-01", periods=len(rows), freq="15min", tz="UTC")
    candles = pd.DataFrame(rows)
    candles["ts"] = ts

    class _ColPreset(_FakePreset):
        def generate_signals(
            self, candles: pd.DataFrame, params: dict[str, Any]
        ) -> list[SignalCandidate]:
            last_ts = candles["ts"].iloc[-1]
            if last_ts != self._fire_ts:
                return []
            return [
                SignalCandidate(
                    ts=last_ts,
                    direction=self._direction,
                    ref_entry=self._ref_entry,
                    ref_sl=self._ref_sl,
                    ref_tp=self._ref_tp,
                )
            ]

    preset = _ColPreset(ts[2], "long", ref_entry=100, ref_sl=95, ref_tp=105)
    adapter = SignalStrategyAdapter(preset, window=10)
    sig = adapter.generate_signals(candles, {})
    assert list(sig["entries"]) == [False, False, True, False, False]
    assert list(sig["exits"]) == [False, False, False, False, True]


def test_fixture_loader_deterministic_and_shaped():
    a = load_fixture_candles("btc_15m_3mo")
    b = load_fixture_candles("btc_15m_3mo")
    assert list(a.columns) == ["o", "h", "l", "c", "v"]
    assert isinstance(a.index, pd.DatetimeIndex)
    assert len(a) > 2000  # multi-week
    assert (a["c"] > 0).all()
    assert (a["h"] >= a["l"]).all()
    assert a["v"].nunique() > 1  # rel_volume not constant
    pd.testing.assert_frame_equal(a, b)  # deterministic


def test_fixture_unknown_name_raises():
    with pytest.raises(ValueError):
        load_fixture_candles("nope")


def test_orb_preset_smoke():
    pytest.importorskip("app.strategies.orb")
    from app.strategies.registry import get_strategy

    preset = get_strategy("orb")
    candles = load_fixture_candles("btc_15m_3mo")
    result = run_backtest(
        SignalStrategyAdapter(preset),
        candles,
        preset.default_params(),
        fees_bps=10.0,
        slippage_bps=5.0,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] >= 1
