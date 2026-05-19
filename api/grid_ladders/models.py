from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from pybinbot import ExchangeId, GridLadderStatus, MarketType


class GridLadderCreate(BaseModel):
    symbol: str = Field(min_length=1)
    fiat: str = Field(default="USDC", min_length=1)
    exchange: ExchangeId = Field(default=ExchangeId.KUCOIN)
    market_type: MarketType = Field(default=MarketType.FUTURES)
    algorithm_name: str = Field(default="fixed_grid", min_length=1)
    range_low: float = Field(gt=0)
    range_high: float = Field(gt=0)
    level_count: int = Field(ge=3)
    total_margin: float = Field(gt=0)
    breakout_low: float = Field(gt=0)
    breakout_high: float = Field(gt=0)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol", "fiat", mode="before")
    @classmethod
    def normalize_symbols(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_range(self) -> "GridLadderCreate":
        if self.range_low >= self.range_high:
            raise ValueError("range_low must be less than range_high")
        if self.breakout_low >= self.range_low:
            raise ValueError("breakout_low must be less than range_low")
        if self.breakout_high <= self.range_high:
            raise ValueError("breakout_high must be greater than range_high")
        return self


class GridLadderCloseRequest(BaseModel):
    reason: str = Field(default="manual_close")


class GridLevelRecord(BaseModel):
    id: UUID
    ladder_id: UUID
    level_index: int
    price: float
    side: str
    contracts: int
    margin_required: float
    status: str
    entry_order_id: str | None = None
    take_profit_order_id: str | None = None
    filled_entry_price: float | None = None
    filled_entry_qty: float
    take_profit_price: float | None = None
    realized_pnl: float
    created_at: float
    updated_at: float

    model_config = {"from_attributes": True}


class GridLadderRecord(BaseModel):
    id: UUID
    symbol: str
    fiat: str
    exchange: ExchangeId
    market_type: MarketType
    algorithm_name: str
    status: GridLadderStatus
    range_low: float
    range_high: float
    grid_step: float
    level_count: int
    total_margin: float
    reserved_margin: float
    used_margin: float
    realized_pnl: float
    unrealized_pnl: float
    breakout_low: float
    breakout_high: float
    created_at: float
    updated_at: float
    closed_at: float | None = None
    context: dict[str, Any]
    levels: list[GridLevelRecord] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class GridLadderResponse(BaseModel):
    detail: GridLadderRecord | None = None


class GridLadderListResponse(BaseModel):
    detail: list[GridLadderRecord] = Field(default_factory=list)
