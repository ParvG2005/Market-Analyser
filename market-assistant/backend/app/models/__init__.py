from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so they register on Base.metadata (e.g. for alembic env target_metadata).
from app.models.candle import CandleRow  # noqa: E402
from app.models.instrument import Instrument  # noqa: E402

__all__ = ["Base", "CandleRow", "Instrument"]
