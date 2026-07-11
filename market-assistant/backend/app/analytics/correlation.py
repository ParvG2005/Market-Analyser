from typing import TypedDict

import pandas as pd


class CorrelationMatrix(TypedDict):
    symbols: list[str]
    matrix: list[list[float]]


def compute_correlation_matrix(
    returns_by_symbol: dict[str, pd.Series],
) -> CorrelationMatrix:
    symbols = list(returns_by_symbol.keys())
    frame = pd.DataFrame(
        {sym: series.reset_index(drop=True) for sym, series in returns_by_symbol.items()}
    )
    corr = frame.corr(method="pearson")
    matrix = [
        [round(float(corr.loc[row, col]), 6) for col in symbols] for row in symbols
    ]
    return {"symbols": symbols, "matrix": matrix}
