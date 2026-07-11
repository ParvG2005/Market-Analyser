import pandas as pd


class LeakageError(Exception):
    """Raised when a feature's timestamp is at or after its paired
    label's timestamp — i.e. the model would see the future."""


def assert_no_leakage(features: pd.DataFrame, labels: pd.DataFrame) -> None:
    if len(features) != len(labels):
        raise ValueError(
            f"features ({len(features)} rows) and labels ({len(labels)} rows) "
            "must be row-aligned and equal length"
        )

    feature_ts = features["feature_ts"].reset_index(drop=True)
    label_ts = labels["label_ts"].reset_index(drop=True)

    violations = feature_ts >= label_ts
    if violations.any():
        bad_rows = violations[violations].index.tolist()
        first = bad_rows[0]
        raise LeakageError(
            f"leakage detected at row {first} (and {len(bad_rows) - 1} more): "
            f"feature_ts={feature_ts[first]} >= label_ts={label_ts[first]}"
        )
