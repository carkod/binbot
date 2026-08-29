from datetime import datetime
from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import SQLModel, Field


class TopGainersLosersSeriesTable(SQLModel, table=True):
    """
    One row per (recorded_at, side, rank) — a symbol's 24h price change
    percent captured in an hourly top-10 gainers/losers snapshot, so patterns
    across days can be queried directly in SQL for future strategy analysis.
    """

    __tablename__ = "top_gainers_losers_series"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "recorded_at",
            "side",
            "rank",
            name="uq_top_gainers_losers_series_source_recorded_at_side_rank",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(
        default="kucoin_futures",
        nullable=False,
        max_length=32,
        index=True,
        description="Market venue and product used to build the ranking",
    )
    recorded_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    side: str = Field(
        nullable=False, max_length=8, index=True, description="gainer|loser"
    )
    rank: int = Field(nullable=False, description="1 = biggest gain/loss")
    symbol: str = Field(nullable=False, max_length=64, index=True)
    price_change_percent: float = Field(nullable=False)
