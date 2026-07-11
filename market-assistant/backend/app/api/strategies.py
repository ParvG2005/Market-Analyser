import uuid
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtest.signal_bridge import run_signal_backtest
from app.core.auth import get_current_user_id
from app.core.deps import get_session
from app.models.candle import CandleRow
from app.models.signal import Signal
from app.models.strategy_config import StrategyConfig
from app.scanner.history import load_recent_candles
from app.schemas.strategy import (
    MiniBacktestRequest,
    MiniBacktestResponse,
    SignalOut,
    StrategyConfigIn,
    StrategyConfigOut,
    StrategyMeta,
)
from app.strategies.registry import get_strategy, list_strategies

router = APIRouter(prefix="/api", tags=["strategies"])

_MINI_BACKTEST_HISTORY_BARS = 2000


def _require_strategy(name: str) -> Any:
    """Look up a preset, mapping the registry's KeyError to a 422 (the repo's
    validation-error convention; there is no global KeyError handler)."""
    try:
        return get_strategy(name)
    except KeyError as e:
        raise HTTPException(
            status_code=422, detail=f"unknown strategy: {name}"
        ) from e


def _f(value: Any) -> float:
    """Coerce a candle OHLCV cell (Decimal, never None in practice) to float."""
    return float(value)


def _candles_to_df(rows: list[CandleRow]) -> pd.DataFrame:
    """Build the float-OHLCV + datetime ``ts`` DataFrame the presets expect,
    matching the signal worker's construction."""
    return pd.DataFrame(
        [
            {
                "ts": r.ts,
                "o": _f(r.o),
                "h": _f(r.h),
                "l": _f(r.l),
                "c": _f(r.c),
                "v": _f(r.v),
            }
            for r in rows
        ]
    )


@router.get("/strategies", response_model=list[StrategyMeta])
async def get_strategies() -> list[StrategyMeta]:
    return [
        StrategyMeta(
            name=s.name,
            label=s.name.replace("_", " ").title(),
            regime_mode=s.regime_mode,
            param_schema=s.param_schema(),
            default_params=s.default_params(),
        )
        for s in list_strategies()
    ]


@router.post(
    "/strategy-configs",
    response_model=StrategyConfigOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_strategy_config(
    body: StrategyConfigIn,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> StrategyConfig:
    _require_strategy(body.strategy)
    cfg = StrategyConfig(user_id=user_id, **body.model_dump())
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    return cfg


@router.get("/strategy-configs", response_model=list[StrategyConfigOut])
async def list_strategy_configs(
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[StrategyConfig]:
    result = await session.execute(
        select(StrategyConfig).where(StrategyConfig.user_id == user_id)
    )
    return list(result.scalars().all())


@router.patch("/strategy-configs/{config_id}", response_model=StrategyConfigOut)
async def update_strategy_config(
    config_id: int,
    body: StrategyConfigIn,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> StrategyConfig:
    cfg = await session.get(StrategyConfig, config_id)
    # Per-user ownership: a config owned by another user is indistinguishable
    # from a missing one (mirror the scanner's cross-user -> 404).
    if cfg is None or cfg.user_id != user_id:
        raise HTTPException(status_code=404, detail="strategy config not found")
    _require_strategy(body.strategy)
    for key, value in body.model_dump().items():
        setattr(cfg, key, value)
    await session.commit()
    await session.refresh(cfg)
    return cfg


@router.get("/signals", response_model=list[SignalOut])
async def get_signals(
    instrument_id: int,
    strategy: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Signal]:
    query = select(Signal).where(Signal.instrument_id == instrument_id)
    if strategy:
        query = query.where(Signal.strategy == strategy)
    result = await session.execute(query.order_by(Signal.ts.desc()).limit(50))
    return list(result.scalars().all())


@router.post(
    "/strategies/{strategy_name}/backtest", response_model=MiniBacktestResponse
)
async def mini_backtest(
    strategy_name: str,
    body: MiniBacktestRequest,
    session: AsyncSession = Depends(get_session),
) -> MiniBacktestResponse:
    """Synchronous, HONEST mini-backtest for the frontend win-rate cards.

    Deliberately uses ``run_signal_backtest`` (TP/SL-resolved, directional,
    cost-aware) rather than Phase 5's async close-to-close ``run_backtest``.
    """
    strat = _require_strategy(strategy_name)
    rows = await load_recent_candles(
        session, body.instrument_id, body.tf, limit=_MINI_BACKTEST_HISTORY_BARS
    )
    if not rows:
        raise HTTPException(
            status_code=404, detail="no candle history for instrument/tf"
        )
    df = _candles_to_df(rows)
    result = run_signal_backtest(
        strat,
        df,
        body.params or strat.default_params(),
        fees_bps=body.fees_bps,
        slippage_bps=body.slippage_bps,
        window=body.window,
    )
    return MiniBacktestResponse(
        stats={k: float(v) for k, v in result.stats.items()},
        n_candles=len(rows),
    )
