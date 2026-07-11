from typing import Any
from uuid import UUID

from pydantic import BaseModel


class StrategyMeta(BaseModel):
    name: str
    label: str
    regime_mode: str  # "trend" | "range" | "any"
    param_schema: dict[str, Any]
    default_params: dict[str, Any]


class StrategyConfigIn(BaseModel):
    strategy: str
    instrument_id: int
    tf: str
    params: dict[str, Any]
    enabled: bool = True


class StrategyConfigOut(StrategyConfigIn):
    id: int
    user_id: UUID


class SignalOut(BaseModel):
    id: int
    instrument_id: int | None
    strategy: str
    direction: str
    ts: str
    confidence: float | None
    ref_entry: float | None
    ref_sl: float | None
    ref_tp: float | None
    backtest_ref: str | None
    meta: dict[str, Any] | None
