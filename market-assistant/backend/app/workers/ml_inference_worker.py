import uuid
from typing import Any

import pandas as pd

from app.ml.features import build_features
from app.ml.inference import predict_prob_up, should_emit_signal
from app.ml.registry import load_artifact
from app.ml.train import FEATURE_COLUMNS
from app.models.ml_model import MLModel
from app.models.signal import Signal


async def run_ml_inference_job(
    ctx: dict[str, Any], ml_model_id: str, instrument_id: int, candles_window: pd.DataFrame
) -> None:
    db_session = ctx["db_session"]
    ml_model = await db_session.get(MLModel, uuid.UUID(ml_model_id))
    if ml_model is None or not ml_model.published:
        return

    artifact = load_artifact(ml_model.artifact_path)
    model, calibrator = artifact["model"], artifact["calibrator"]

    features = build_features(candles_window)
    if features.empty:
        return

    latest_row = features[FEATURE_COLUMNS].iloc[[-1]]
    prob_up = predict_prob_up(model, calibrator, latest_row)

    threshold = (ml_model.metrics or {}).get("threshold", 0.55)
    if not should_emit_signal(ml_model.published, prob_up, threshold):
        return

    signal = Signal(
        instrument_id=instrument_id,
        strategy="ml_lgbm_v1",
        direction="long",
        ts=features.index[-1],
        confidence=prob_up,
        meta={
            "model_id": str(ml_model.id),
            "baseline": {
                "model_net_return": (ml_model.metrics or {}).get("model_net_return"),
                "buy_hold_return": (ml_model.metrics or {}).get("buy_hold_return"),
                "random_return": (ml_model.metrics or {}).get("random_return"),
            },
        },
    )
    db_session.add(signal)
    await db_session.commit()
