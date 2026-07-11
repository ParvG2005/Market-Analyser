import pandas as pd

from app.strategies.orb import ORBStrategy


def _bar(
    ts: str, o: float, h: float, l: float, c: float, v: float  # noqa: E741
) -> dict[str, object]:
    return {"ts": pd.Timestamp(ts), "o": o, "h": h, "l": l, "c": c, "v": v}


def test_orb_golden_breakout_fires_one_long_signal() -> None:
    # First 4 bars (09:15-10:00) define the opening range: high=105, low=100.
    bars = [
        _bar("2024-01-01T09:15", 101, 103, 100, 102, 1000),
        _bar("2024-01-01T09:30", 102, 105, 101, 104, 1000),
        _bar("2024-01-01T09:45", 104, 104, 102, 103, 1000),
        _bar("2024-01-01T10:00", 103, 104, 102, 103, 1000),
        # breakout bar: closes above OR high 105, on 3x average volume
        _bar("2024-01-01T10:15", 104, 108, 104, 107, 3000),
    ]
    candles = pd.DataFrame(bars)
    strat = ORBStrategy()
    signals = strat.generate_signals(candles, strat.default_params())

    assert len(signals) == 1
    sig = signals[0]
    assert sig.direction == "long"
    assert sig.ref_entry == 107
    assert sig.ref_sl == 100  # opening range low
    assert sig.ref_tp == 107 + (107 - 100) * 2.0  # default rr=2.0


def test_orb_negative_breakout_without_volume_confirm_fires_nothing() -> None:
    bars = [
        _bar("2024-01-01T09:15", 101, 103, 100, 102, 1000),
        _bar("2024-01-01T09:30", 102, 105, 101, 104, 1000),
        _bar("2024-01-01T09:45", 104, 104, 102, 103, 1000),
        _bar("2024-01-01T10:00", 103, 104, 102, 103, 1000),
        # closes above OR high but volume is flat (no confirm)
        _bar("2024-01-01T10:15", 104, 106, 104, 106, 1000),
    ]
    candles = pd.DataFrame(bars)
    strat = ORBStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert signals == []
