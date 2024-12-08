import json
from uuid import uuid4, UUID
from time import time
from typing import TYPE_CHECKING, List, Optional
from pydantic import Json, field_serializer, field_validator
from sqlalchemy import JSON, Column, Enum
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
    fiat: str = Field(default="USDC")
    # Min Binance 0.0001 BNB
    base_order_size: float = Field(default=15)
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
        sa_column=Column(Enum(CloseConditions)),
    )
    # cooldown period in minutes before opening next bot with same pair
    cooldown: int = Field(default=0)
    created_at: float = Field(default_factory=lambda: time() * 1000)
    updated_at: float = Field(default_factory=lambda: time() * 1000)
    deal: Optional["DealTable"] = Relationship(back_populates="bot")
    dynamic_trailling: bool = Field(default=False)
    logs: List[Json[str]] = Field(default=[], sa_column=Column(JSON))
    mode: str = Field(default="manual")
    name: str = Field(default="Default bot")
    # filled up internally
    orders: Optional[List["ExchangeOrderTable"]] = Relationship(back_populates="bot")
    status: str = Field(default=Status.inactive, sa_column=Column(Enum(Status)))
    stop_loss: float = Field(default=0, gt=0)
    # If stop_loss > 0, allow for reversal
    margin_short_reversal: bool = Field(default=False)
    take_profit: float = Field(default=0, gt=0)
    trailling: bool = Field(default=False)
    trailling_deviation: float = Field(default=0, gt=0)
    # Trailling activation (first take profit hit)
    trailling_profit: float = Field(default=0, gt=0)
    strategy: str = Field(default=Strategy.long, sa_column=Column(Enum(Strategy)))
    short_buy_price: float = Field(default=0)
    # autoswitch to short_strategy
    short_sell_price: float = Field(default=0)
    total_commission: float = Field(default=0)

    model_config = {
        "arbitrary_types_allowed": True,
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

    @field_validator("base_order_size")
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

    @field_validator(
        "stop_loss",
        "take_profit",
        "trailling_deviation",
        "trailling_profit",
        mode="before",
    )
    @classmethod
    def check_percentage(cls, v):
        if 0 <= float(v) < 100:
            return v
        else:
            raise ValueError(f"{v} must be a percentage")

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

    @field_serializer("logs")
    @classmethod
    def logs_serializer(cls, v):
        return json.loads(v)
