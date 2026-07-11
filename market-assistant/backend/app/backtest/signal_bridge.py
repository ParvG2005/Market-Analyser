"""Faithful SignalCandidate -> backtest bridge.

Phase-6 presets emit ``list[SignalCandidate]`` (one-shot entry/SL/TP
setups). Phase-5 ``run_backtest`` wants a ``Strategy`` whose
``generate_signals`` returns a bool ``entries``/``exits`` DataFrame. This
adapter walks bars left->right and performs a faithful RR/SL-TP
walk-forward so the win-rate/net-return stats shown on user cards are
decided by whether TP or SL was hit first -- not by a fixed hold.
"""

from typing import Any, Protocol

import pandas as pd

from app.strategies.base import SignalCandidate


class _SignalPreset(Protocol):
    name: str

    def generate_signals(
        self, candles: pd.DataFrame, params: dict[str, Any]
    ) -> list[SignalCandidate]: ...


class SignalStrategyAdapter:
    """Adapts a Phase-6 SignalCandidate preset to the Phase-5 backtest
    Strategy protocol via a faithful RR/SL-TP walk-forward.

    Walk bars left->right; while flat, feed the preset a trailing window
    ending at the current bar; if it returns a signal whose ``ts`` is the
    current bar (a fresh setup on this bar), OPEN a position at this bar
    (``entries[i]=True``) recording direction/ref_sl/ref_tp. While in a
    position, close (``exits[j]=True``) on the FIRST later bar that touches
    TP or SL: long -> ``high>=tp`` is a win, ``low<=sl`` is a loss (both in
    the same bar resolves as SL-first = conservative loss); short ->
    ``low<=tp`` win, ``high>=sl`` loss. One position at a time; new signals
    are ignored while in a position. Signals not tied to the current bar
    are ignored. A position still open at the last bar is left open
    (``run_backtest`` only counts closed trades).
    """

    def __init__(self, preset: _SignalPreset, window: int = 60) -> None:
        self.preset = preset
        self.window = window
        self.name = f"{preset.name}_signal_bt"

    @staticmethod
    def _timestamps(candles: pd.DataFrame) -> pd.Series | pd.Index:
        """Per-bar timestamps: prefer a DatetimeIndex, else a ``ts`` column."""
        if isinstance(candles.index, pd.DatetimeIndex):
            return candles.index
        if "ts" in candles.columns:
            return candles["ts"]
        raise ValueError("candles must have a DatetimeIndex or a 'ts' column")

    def generate_signals(self, candles: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        n = len(candles)
        entries = [False] * n
        exits = [False] * n

        ts = self._timestamps(candles)
        highs = candles["h"].to_numpy(dtype=float)
        lows = candles["l"].to_numpy(dtype=float)

        in_position = False
        direction = ""
        sl = 0.0
        tp = 0.0

        for i in range(n):
            if not in_position:
                start = max(0, i - self.window + 1)
                window_df = candles.iloc[start : i + 1]
                signals = self.preset.generate_signals(window_df, params)
                current_ts = ts[i]
                fresh = next((s for s in signals if s.ts == current_ts), None)
                if fresh is not None:
                    entries[i] = True
                    in_position = True
                    direction = fresh.direction
                    sl = float(fresh.ref_sl)
                    tp = float(fresh.ref_tp)
                # An entry bar is never also an exit bar: touch checks start
                # on the next bar.
                continue

            hi = highs[i]
            lo = lows[i]
            if direction == "long":
                hit_sl = lo <= sl
                hit_tp = hi >= tp
            else:  # short
                hit_sl = hi >= sl
                hit_tp = lo <= tp

            # SL-first (conservative) when both touch in the same bar.
            if hit_sl or hit_tp:
                exits[i] = True
                in_position = False

        return pd.DataFrame({"entries": entries, "exits": exits}, index=candles.index)
