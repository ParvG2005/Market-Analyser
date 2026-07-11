import hashlib
import json

import pandas as pd


def serialize_equity_curve(equity_curve: pd.Series) -> list[dict]:
    return [
        {"ts": ts.isoformat(), "value": float(value)}
        for ts, value in equity_curve.items()
    ]


def stats_hash(stats: dict) -> str:
    canonical = json.dumps(stats, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
