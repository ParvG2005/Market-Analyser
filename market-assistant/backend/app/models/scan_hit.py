from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ScanHit(Base):
    __tablename__ = "scan_hits"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("scan_rules.id"))
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instruments.id"))
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
