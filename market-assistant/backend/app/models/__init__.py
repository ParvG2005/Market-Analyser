from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so they register on Base.metadata (e.g. for alembic env target_metadata).
from app.models.backtest import Backtest  # noqa: E402
from app.models.candle import CandleRow  # noqa: E402
from app.models.instrument import Instrument  # noqa: E402
from app.models.ml_model import MLModel  # noqa: E402
from app.models.news_item import NewsItem  # noqa: E402
from app.models.scan_hit import ScanHit  # noqa: E402
from app.models.scan_rule import ScanRule  # noqa: E402
from app.models.signal import Signal  # noqa: E402
from app.models.strategy_config import StrategyConfig  # noqa: E402

__all__ = [
    "Backtest",
    "Base",
    "CandleRow",
    "Instrument",
    "MLModel",
    "NewsItem",
    "ScanHit",
    "ScanRule",
    "Signal",
    "StrategyConfig",
]
