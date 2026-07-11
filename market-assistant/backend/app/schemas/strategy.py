from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

    @field_validator("ts", mode="before")
    @classmethod
    def _coerce_ts(cls, value: Any) -> Any:
        # ORM Signal.ts is a datetime (TIMESTAMPTZ) but the wire shape is an ISO
        # string; coerce so returning an ORM object via response_model serializes.
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_validator("backtest_ref", mode="before")
    @classmethod
    def _coerce_backtest_ref(cls, value: Any) -> Any:
        # ORM Signal.backtest_ref is a UUID; the wire shape is a string.
        if value is None:
            return None
        return str(value)


class MiniBacktestRequest(BaseModel):
    instrument_id: int
    tf: str
    params: dict[str, Any] | None = None
    fees_bps: int = 10
    slippage_bps: int = 5
    window: int = 60


class MiniBacktestResponse(BaseModel):
    stats: dict[str, float]
    n_candles: int
