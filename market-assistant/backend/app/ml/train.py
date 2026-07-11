from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.backtest.leakage import assert_no_leakage
from app.ml.baseline import buy_and_hold_return, passes_baseline_gate, random_baseline_return
from app.ml.calibration import apply_calibrator, fit_calibrator
from app.ml.evaluate import simulate_directional_returns
from app.ml.features import build_features
from app.ml.labels import build_fixed_horizon_labels
from app.ml.registry import save_artifact
from app.ml.splitter import purged_walk_forward_splits

FEATURE_COLUMNS = [
    "ret_1",
    "ret_3",
    "ret_5",
    "vol_10",
    "rsi_14",
    "volume_z",
    "vwap_dist",
    "regime_trend_up",
    "regime_trend_down",
    "regime_range",
    "regime_high_vol",
]


def default_lgbm_classifier() -> Any:
    import lightgbm as lgb

    return lgb.LGBMClassifier(n_estimators=100, num_leaves=15, learning_rate=0.05, random_state=42)


@dataclass(frozen=True)
class TrainResult:
    fold_metrics: list[dict[str, Any]]
    feature_importances: dict[str, float]
    model_net_return: float
    buy_hold_return: float
    random_return: float
    published: bool
    artifact_path: str
    threshold: float


def train_model(
    candles: pd.DataFrame,
    regime: pd.Series | None,
    instrument_group: str,
    version: str,
    horizon: int,
    n_splits: int,
    test_size: int,
    purge: int,
    fees_bps: float,
    slippage_bps: float,
    threshold: float = 0.55,
    classifier_factory: Callable[[], Any] = default_lgbm_classifier,
    artifact_base_dir: Path | None = None,
) -> TrainResult:
    features = build_features(candles, regime=regime)
    labels = build_fixed_horizon_labels(candles, horizon=horizon)

    joined = features.join(labels, how="inner")
    assert_no_leakage(
        joined.rename(columns={"feature_ts": "feature_ts"}),
        joined[["label_ts"]],
    )

    X = joined[FEATURE_COLUMNS].reset_index(drop=True)
    y = joined["y"].reset_index(drop=True).to_numpy()
    close_aligned = candles["c"].reindex(joined.index).to_numpy()

    n = len(X)
    splits = purged_walk_forward_splits(
        n_samples=n, n_splits=n_splits, test_size=test_size, purge=purge
    )

    fold_metrics: list[dict[str, Any]] = []
    oof_raw = np.full(n, np.nan)
    oof_mask = np.zeros(n, dtype=bool)

    for fold_i, (train_idx, test_idx) in enumerate(splits):
        clf = classifier_factory()
        clf.fit(X.iloc[train_idx], y[train_idx])
        raw_test = clf.predict_proba(X.iloc[test_idx])[:, 1]

        oof_raw[test_idx] = raw_test
        oof_mask[test_idx] = True

        preds = (raw_test >= 0.5).astype(int)
        accuracy = float((preds == y[test_idx]).mean())
        fold_metrics.append(
            {
                "fold": fold_i,
                "n_train": len(train_idx),
                "n_test": len(test_idx),
                "accuracy": accuracy,
            }
        )

    oof_idx = np.where(oof_mask)[0]
    raw_oof = oof_raw[oof_idx]
    y_oof = y[oof_idx]

    if len(set(raw_oof.tolist())) > 1:
        calibrator = fit_calibrator(raw_oof, y_oof)
        calibrated_oof = apply_calibrator(calibrator, raw_oof)
    else:
        # Degenerate case (constant raw output across the OOF set): isotonic
        # regression on a single unique x is undefined-in-spirit (it would
        # just return mean(y)), so fall back to the raw constant directly.
        calibrator = None
        calibrated_oof = raw_oof

    entries_mask_full = np.zeros(n, dtype=bool)
    entries_mask_full[oof_idx] = calibrated_oof >= threshold

    model_net_return = simulate_directional_returns(
        close_aligned,
        entries_mask_full,
        horizon=horizon,
        fees_bps=fees_bps,
        slippage_bps=slippage_bps,
    )

    oof_candles = (
        candles.reindex(joined.index).iloc[oof_idx[0] : oof_idx[-1] + 1]
        if len(oof_idx)
        else candles.iloc[:1]
    )
    buy_hold = buy_and_hold_return(oof_candles, fees_bps=fees_bps, slippage_bps=slippage_bps)
    random_return = random_baseline_return(
        oof_candles, fees_bps=fees_bps, slippage_bps=slippage_bps
    )

    published = passes_baseline_gate(model_net_return, buy_hold, random_return)

    final_model = classifier_factory()
    final_model.fit(X, y)
    importances = getattr(final_model, "feature_importances_", None)
    if importances is not None:
        feature_importances = dict(zip(FEATURE_COLUMNS, [float(v) for v in importances]))
    else:
        feature_importances = {col: 0.0 for col in FEATURE_COLUMNS}

    artifact_path = save_artifact(
        {"model": final_model, "calibrator": calibrator},
        instrument_group=instrument_group,
        version=version,
        base_dir=artifact_base_dir,
    )

    return TrainResult(
        fold_metrics=fold_metrics,
        feature_importances=feature_importances,
        model_net_return=model_net_return,
        buy_hold_return=buy_hold,
        random_return=random_return,
        published=published,
        artifact_path=artifact_path,
        threshold=threshold,
    )
