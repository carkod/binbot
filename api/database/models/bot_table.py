import json
from uuid import uuid4, UUID
from typing import TYPE_CHECKING, List, Optional
from pydantic import Json, PositiveInt, field_serializer, field_validator
from sqlalchemy import JSON, Column, Enum
from database.utils import timestamp
from tools.enum_definitions import (
    BinanceKlineIntervals,
    BinbotEnums,
    CloseConditions,
    Status,
    Strategy,
)
from sqlmodel import Relationship, SQLModel, Field

# avoids circular imports
# https://sqlmodel.tiangolo.com/tutorial/code-structure/#hero-model-file
if TYPE_CHECKING:
    from database.models.deal_table import DealTable
    from database.models.order_table import ExchangeOrderTable


class BotTable(SQLModel, table=True):
    __tablename__ = "bot"

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    pair: str = Field(index=True)
    fiat: str = Field(default="USDC", index=True)
    base_order_size: float = Field(default=15, description="Min Binance 0.0001 BNB approx 15USD")
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
        sa_column=Column(Enum(CloseConditions)),
    )
    cooldown: PositiveInt = Field(default=0, description="cooldown period in minutes before opening next bot with same pair")
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
    deal: "DealTable" = Relationship(back_populates="bot")
    dynamic_trailling: bool = Field(default=False)
    logs: List[Json[str]] = Field(default=[], sa_column=Column(JSON))
    mode: str = Field(default="manual")
    name: str = Field(default="Default bot")
    # filled up internally by Exchange
    orders: List["ExchangeOrderTable"] = Relationship(back_populates="bot")
    status: str = Field(default=Status.inactive, sa_column=Column(Enum(Status)))
    stop_loss: float = Field(default=0, description="If stop_loss > 0, allow for reversal")
    margin_short_reversal: Optional[bool] = Field(default=False)
    take_profit: float = Field(default=0)
    trailling: bool = Field(default=False)
    trailling_deviation: Optional[float] = Field(default=0, ge=-1, le=101)
    # Trailling activation (first take profit hit)
    trailling_profit: Optional[float] = Field(default=0)
    strategy: str = Field(default=Strategy.long, sa_column=Column(Enum(Strategy)))
    short_buy_price: float = Field(default=0)
    # autoswitch to short_strategy
    short_sell_price: float = Field(default=0)
    total_commission: float = Field(default=0)

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "description": "Most fields are optional. Deal field is generated internally, orders are filled up by Exchange",
            "examples": [
                {
                    "pair": "BNBUSDT",
                    "fiat": "USDC",
                    "base_order_size": 15,
                    "candlestick_interval": "15m",
                    "cooldown": 0,
                    "logs": [],
                    # Manual is triggered by the terminal dashboard, autotrade by research app,
                    "mode": "manual",
                    "name": "Default bot",
                    "orders": [],
                    "status": "inactive",
                    "stop_loss": 0,
                    "take_profit": 2.3,
                    "trailling": "true",
                    "trailling_deviation": 0.63,
                    "trailling_profit": 2.3,
                    "strategy": "long",
                    "short_buy_price": 0,
                    "short_sell_price": 0,
                    "total_commission": 0,
                }
            ],
        },
    }

    @field_validator("pair", "candlestick_interval")
    @classmethod
    def check_names_not_empty(cls, v):
        assert v != "", "Empty pair field."
        return v

    @field_validator("base_order_size", "short_buy_price", "short_sell_price", "total_commission")
    @classmethod
    def countables(cls, v):
        if isinstance(v, float):
            return v
        elif isinstance(v, str):
            return float(v)
        elif isinstance(v, int):
            return float(v)
        else:
            raise ValueError(f"{v} must be a number (float, int or string)")

    @field_validator("mode")
    @classmethod
    def check_mode(cls, v: str):
        if v not in BinbotEnums.mode:
            raise ValueError(f'Status must be one of {", ".join(BinbotEnums.mode)}')
        return v

    @field_validator("strategy")
    @classmethod
    def check_strategy(cls, v: str):
        if v not in BinbotEnums.strategy:
            raise ValueError(f'Status must be one of {", ".join(BinbotEnums.strategy)}')
        return v

    @field_validator("trailling")
    @classmethod
    def booleans(cls, v: bool):
        if isinstance(v, bool):
            return v
        else:
            raise ValueError(f"{v} must be a boolean")

    @field_validator("logs", mode="before")
    @classmethod
    def parse_logs(cls, v):
        if isinstance(v, list):
            return v
        else:
            return []

    @field_serializer("logs")
    @classmethod
    def logs_serializer(cls, v):
        if isinstance(v, str):
            return json.loads(v)
