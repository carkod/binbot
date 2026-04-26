from uuid import UUID, uuid4
from typing import Optional
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field
from pybinbot import timestamp


class StrategyThresholdOverrideTable(SQLModel, table=True):
    __tablename__ = "strategy_threshold_override"

    id: Optional[UUID] = Field(
        default_factory=uuid4,
        primary_key=True,
        nullable=False,
        unique=True,
        index=True,
    )
    strategy_name: str = Field(index=True)
    symbol: str = Field(index=True)
    buy_trigger_pct: float = Field(ge=0)
    sell_trigger_pct: float = Field(ge=0)
    profile: str = Field(default="")
    source_provider: str = Field(default="manual", index=True)
    market_context_timestamp: float = Field(default_factory=timestamp)
    expires_at: float = Field(index=True)
    confidence: float = Field(default=0, ge=0, le=1)
    reason: str = Field(default="")
    raw_model_response: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: float = Field(default_factory=timestamp)
