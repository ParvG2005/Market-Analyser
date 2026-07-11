import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BacktestCreateRequest(BaseModel):
    strategy: str
    params: dict[str, Any]
    universe: dict[str, Any]
    start_ts: datetime
    end_ts: datetime
    fees_bps: float = Field(..., gt=0, description="Trading fee in bps; must be > 0")
    slippage_bps: float = Field(..., gt=0, description="Slippage in bps; must be > 0")


class BacktestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    stats: dict[str, Any] | None = None
    equity_curve: list[dict[str, Any]] | None = None
