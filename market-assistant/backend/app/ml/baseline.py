import numpy as np
import pandas as pd

from app.backtest.costs import apply_costs
from app.ml.evaluate import simulate_directional_returns


def buy_and_hold_return(candles: pd.DataFrame, fees_bps: float, slippage_bps: float) -> float:
    entry = candles["c"].iloc[0]
    exit_ = candles["c"].iloc[-1]
    costs = apply_costs(
        entry_price=float(entry),
        exit_price=float(exit_),
        fees_bps=fees_bps,
        slippage_bps=slippage_bps,
        side="long",
    )
    return costs.net_pnl / float(entry)


def random_baseline_return(
    candles: pd.DataFrame,
    fees_bps: float,
    slippage_bps: float,
    n_trials: int = 200,
    seed: int = 42,
) -> float:
    rng = np.random.default_rng(seed)
    close = candles["c"].to_numpy()
    n = len(close)

    trial_returns = []
    for _ in range(n_trials):
        entries_mask = rng.integers(0, 2, size=n).astype(bool)
        trial_returns.append(
            simulate_directional_returns(
                close, entries_mask, horizon=1, fees_bps=fees_bps, slippage_bps=slippage_bps
            )
        )
    return float(np.mean(trial_returns))


def passes_baseline_gate(
    model_net_return: float, buy_hold_return: float, random_return: float
) -> bool:
    # Wrap in bool(): the inputs may be numpy floats, whose comparisons yield
    # numpy bools that fail strict `is True`/`is False` identity checks.
    return bool(model_net_return > buy_hold_return and model_net_return > random_return)
