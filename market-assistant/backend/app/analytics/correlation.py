from typing import TypedDict

import pandas as pd


class CorrelationMatrix(TypedDict):
    symbols: list[str]
    matrix: list[list[float]]


def compute_correlation_matrix(
    returns_by_symbol: dict[str, pd.Series],
) -> CorrelationMatrix:
    symbols = list(returns_by_symbol.keys())
    # Align on the timestamp INDEX, never by position: instruments have
    # different histories/gaps, so pairing the i-th bar of each series
    # correlates unrelated points. Building the frame from the ts-indexed
    # series unions on timestamp; corr() then uses pairwise-complete overlap.
    frame = pd.DataFrame(returns_by_symbol)
    corr = frame.corr(method="pearson")
    matrix = [
        [round(float(corr.loc[row, col]), 6) for col in symbols] for row in symbols
    ]
    return {"symbols": symbols, "matrix": matrix}
