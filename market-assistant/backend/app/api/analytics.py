from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.correlation import CorrelationMatrix, compute_correlation_matrix
from app.analytics.seasonality import Seasonality, compute_seasonality
from app.core.deps import get_session
from app.models.candle import CandleRow
from app.models.instrument import Instrument

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


async def _load_closes(
    session: AsyncSession, instrument_id: int, tf: str, limit: int
) -> pd.DataFrame:
    query = (
        select(CandleRow.ts, CandleRow.c)
        .where(CandleRow.instrument_id == instrument_id, CandleRow.tf == tf)
        .order_by(CandleRow.ts.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    rows = list(reversed(result.all()))
    return pd.DataFrame(
        {"ts": [r.ts for r in rows], "c": [float(r.c) for r in rows]}
    )


@router.get("/correlation", response_model=CorrelationMatrix)
async def correlation(
    asset_class: str = Query(...),
    tf: str = "1h",
    # Bounded: need >=2 closes per instrument for pct_change; cap matches the
    # seasonality read ceiling so one caller can't request unbounded rows.
    limit: int = Query(200, ge=2, le=5000),
    session: AsyncSession = Depends(get_session),
) -> CorrelationMatrix:
    query = (
        select(Instrument)
        .where(Instrument.asset_class == asset_class, Instrument.active.is_(True))
        .order_by(Instrument.symbol)
    )
    result = await session.execute(query)
    instruments = result.scalars().all()

    returns_by_symbol: dict[str, pd.Series] = {}
    for instrument in instruments:
        closes = await _load_closes(session, instrument.id, tf, limit)
        if len(closes) < 2:
            continue
        returns_by_symbol[instrument.symbol] = closes["c"].pct_change().dropna()

    if not returns_by_symbol:
        raise HTTPException(status_code=404, detail="no data for asset_class")

    return compute_correlation_matrix(returns_by_symbol)


@router.get("/seasonality", response_model=Seasonality)
async def seasonality(
    symbol: str = Query(...),
    tf: str = "1h",
    bucket: Literal["dow", "month", "hour"] = "dow",
    session: AsyncSession = Depends(get_session),
) -> Seasonality:
    result = await session.execute(select(Instrument).where(Instrument.symbol == symbol))
    instrument = result.scalars().first()
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")

    closes = await _load_closes(session, instrument.id, tf, 5000)
    if len(closes) < 2:
        raise HTTPException(status_code=404, detail="not enough candle data")

    return compute_seasonality(closes, bucket=bucket)
