"""Seven-day execution notional history and inexpensive market minute rollups."""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, Index, String
from sqlmodel import Field, SQLModel

SOURCE = "kucoin_futures"


class CvdBucketTable(SQLModel, table=True):
    __tablename__ = "cvd_bucket"
    __table_args__ = (Index("ix_cvd_bucket_minute", "minute"),)

    source: str = Field(primary_key=True, max_length=32)
    symbol: str = Field(primary_key=True, max_length=64)
    minute: int = Field(sa_column=Column(BigInteger, primary_key=True))
    buy: float = Field(
        default=0, sa_column=Column(Float, nullable=False, server_default="0")
    )
    sell: float = Field(
        default=0, sa_column=Column(Float, nullable=False, server_default="0")
    )
    multiplier: float
    covered: bool = False
    last_trade_ns: int = Field(
        default=0, sa_column=Column(BigInteger, nullable=False, server_default="0")
    )


class CvdMinuteTable(SQLModel, table=True):
    __tablename__ = "cvd_minute"
    __table_args__ = (Index("ix_cvd_minute_minute", "minute"),)

    source: str = Field(primary_key=True, max_length=32)
    minute: int = Field(sa_column=Column(BigInteger, primary_key=True))
    buy: float = 0
    sell: float = 0
    expected_symbols: int
    covered_symbols: int
    universe: str = Field(sa_column=Column(String(64), nullable=False))
    finalized: bool = False
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
