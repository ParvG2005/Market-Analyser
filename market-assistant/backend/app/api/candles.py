from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.candles import CandleOut, Timeframe
from app.core.deps import get_session
from app.models.candle import CandleRow
from app.models.instrument import Instrument

router = APIRouter(tags=["candles"])


@router.get("/candles", response_model=list[CandleOut])
async def get_candles(
    symbol: str,
    tf: Timeframe,
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(...),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[CandleOut]:
    instrument_id = (
        await session.execute(select(Instrument.id).where(Instrument.symbol == symbol))
    ).scalars().first()
    if instrument_id is None:
        return []

    stmt = (
        select(CandleRow)
        .where(
            CandleRow.instrument_id == instrument_id,
            CandleRow.tf == tf.value,
            CandleRow.ts >= from_,
            CandleRow.ts <= to,
        )
        .order_by(CandleRow.ts.asc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [CandleOut.model_validate(row) for row in rows]
