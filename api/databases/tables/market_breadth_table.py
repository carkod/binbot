from datetime import datetime
from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import SQLModel, Field


class MarketBreadthTable(SQLModel, table=True):
    """
    ADR / market-breadth time-series. One row per (timestamp, source) sample,
    written every 30 min by the ingest cron. Stored fields mirror the API
    response 1:1 except adp_ma, which is a rolling window computed on read.
    """

    __tablename__ = "market_breadth"
    __table_args__ = (
        UniqueConstraint("timestamp", "source", name="uq_market_breadth_ts_source"),
    )

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    source: str = Field(nullable=False, max_length=32, index=True)
    advancers: int = Field(nullable=False)
    decliners: int = Field(nullable=False)
    adp: float = Field(nullable=False)
    avg_gain: float = Field(nullable=False)
    avg_loss: float = Field(nullable=False)
    total_volume: float = Field(nullable=False)
    strength_index: float = Field(nullable=False)
