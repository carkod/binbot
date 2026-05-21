from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator
from pybinbot import ExchangeId, MarketType


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
        # Even level_count produces an asymmetric grid (more buys than sells, or
        # vice versa), which breaks the mean-reversion assumption. Require odd.
        if self.level_count % 2 == 0:
            raise ValueError("level_count must be odd for a symmetric grid")
        return self
