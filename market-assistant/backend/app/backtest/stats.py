import math
from typing import Any

import pandas as pd

from app.backtest.costs import TradeCosts

TRADING_PERIODS_PER_YEAR = 252


def compute_stats(equity_curve: pd.Series, trades: list[TradeCosts]) -> dict[str, Any]:
    returns = equity_curve.pct_change().dropna()

    if len(returns) < 2 or returns.std(ddof=1) == 0:
        sharpe = 0.0
    else:
        sharpe = (returns.mean() / returns.std(ddof=1)) * math.sqrt(TRADING_PERIODS_PER_YEAR)

    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1.0
    max_dd = float(drawdown.min())

    trade_count = len(trades)
    wins = sum(1 for t in trades if t.net_pnl > 0)
    win_rate = wins / trade_count if trade_count > 0 else 0.0

    start_equity = float(equity_curve.iloc[0])
    end_equity = float(equity_curve.iloc[-1])
    net_return = (end_equity - start_equity) / start_equity

    return {
        "sharpe": float(sharpe),
        "max_dd": max_dd,
        "win_rate": win_rate,
        "net_return": net_return,
        "trade_count": trade_count,
    }
