from datetime import datetime

from sqlalchemy import Column, DateTime, Index, UniqueConstraint
from sqlmodel import Field, SQLModel


class FuturesPriceSampleTable(SQLModel, table=True):
    """Short rolling history from existing KuCoin futures market requests."""

    __tablename__ = "futures_price_sample"
    __table_args__ = (
        UniqueConstraint(
            "source", "recorded_at", "symbol", name="uq_futures_price_sample_snapshot"
        ),
        Index("ix_futures_price_sample_source_recorded_at", "source", "recorded_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(nullable=False, max_length=32)
    recorded_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    symbol: str = Field(nullable=False, max_length=64)
    last_price: float = Field(nullable=False)
    price_change_percent: float = Field(nullable=False)
    turnover_24h: float = Field(nullable=False)
