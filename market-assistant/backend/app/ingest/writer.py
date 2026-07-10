from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.candle import Candle
from app.models.candle import CandleRow


async def upsert_candles(session: AsyncSession, instrument_id: int, candles: list[Candle]) -> int:
    """Batch upsert candles for one instrument. Idempotent on (instrument_id, tf, ts)."""
    if not candles:
        return 0

    rows = [
        {
            "instrument_id": instrument_id,
            "tf": c.tf,
            "ts": c.ts,
            "o": c.o,
            "h": c.h,
            "l": c.l,
            "c": c.c,
            "v": c.v,
        }
        for c in candles
    ]

    stmt = insert(CandleRow).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[CandleRow.instrument_id, CandleRow.tf, CandleRow.ts],
        set_={
            "o": stmt.excluded.o,
            "h": stmt.excluded.h,
            "l": stmt.excluded.l,
            "c": stmt.excluded.c,
            "v": stmt.excluded.v,
        },
    )
    await session.execute(stmt)
    return len(rows)
