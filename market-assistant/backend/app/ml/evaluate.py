import numpy as np
import numpy.typing as npt

from app.backtest.costs import apply_costs


def simulate_directional_returns(
    close: npt.NDArray[np.float64],
    entries_mask: npt.NDArray[np.bool_],
    horizon: int,
    fees_bps: float,
    slippage_bps: float,
) -> float:
    capital = 1.0
    for i, enter in enumerate(entries_mask):
        if not enter:
            continue
        if i + horizon >= len(close):
            continue
        costs = apply_costs(
            entry_price=float(close[i]),
            exit_price=float(close[i + horizon]),
            fees_bps=fees_bps,
            slippage_bps=slippage_bps,
            side="long",
        )
        capital *= 1 + (costs.net_pnl / close[i])
    return capital - 1.0
