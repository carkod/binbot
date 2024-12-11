from time import time
from typing import Optional

from bson import ObjectId
from deals.models import BinanceOrderModel, DealModel
from tools.enum_definitions import BinanceKlineIntervals, BinbotEnums, CloseConditions, Status, Strategy
from database.models.bot_table import BotTable
from pydantic import BaseModel, Field, field_validator

from tools.handle_error import StandardResponse


class BotResponse(StandardResponse):
    data: BotTable


class BotListResponse(StandardResponse):
    data: list[BotTable]


class ErrorsRequestBody(BaseModel):
    errors: str | list[str]

    @field_validator("errors")
    @classmethod
    def check_names_not_empty(cls, v):
        if isinstance(v, list):
            assert len(v) != 0, "List of errors is empty."
        if isinstance(v, str):
            assert v != "", "Empty pair field."
            return v

        return v


class BotSchema(BaseModel):
    id: str | None = ""
    pair: str
    balance_size_to_use: str | float = 1
    # New table field fiat replaces balance_to_use
    fiat: str = "USDC"
    balance_to_use: str = "USDC"
    base_order_size: float | int = 15  # Min Binance 0.0001 BNB
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes
    )
    close_condition: CloseConditions = Field(default=CloseConditions.dynamic_trailling)
    # cooldown period in minutes before opening next bot with same pair
    cooldown: int = 0
    deal: DealModel = Field(default_factory=DealModel)
    dynamic_trailling: bool = False
    logs: list[str] = []
    # to depricate in new db
    errors: list[str] = []
    # to deprecate in new db
    locked_so_funds: Optional[float] = 0  # funds locked by Safety orders
    mode: str = "manual"
    name: str = "Default bot"
    orders: list[BinanceOrderModel] = []  # Internal
    status: Status = Field(default=Status.inactive)
    stop_loss: float = 0
    margin_short_reversal: bool = False  # If stop_loss > 0, allow for reversal
    take_profit: float = 0
    trailling: bool = True
    trailling_deviation: float = 0
    trailling_profit: float = 0  # Trailling activation (first take profit hit)
    strategy: str = Field(default=Strategy.long)
    short_buy_price: float = 0
    short_sell_price: float = 0  # autoswitch to short_strategy
    # Deal and orders are internal, should never be updated by outside data
    total_commission: float = 0
    created_at: float = time() * 1000
    updated_at: float = time() * 1000

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "description": "Most fields are optional. Deal field is generated internally, orders are filled up by Exchange",
            "examples": [
                {
                    "pair": "BNBUSDT",
                    "balance_size_to_use": 1,
                    "fiat": "USDC",
                    "base_order_size": 15,
                    "candlestick_interval": "15m",
                    "cooldown": 0,
                    "errors": [],
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

    @field_validator(
        "balance_size_to_use", "base_order_size", "base_order_size", mode="before"
    )
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
    def string_booleans(cls, v: str | bool):
        if isinstance(v, str) and v.lower() == "false":
            return False
        if isinstance(v, str) and v.lower() == "true":
            return True
        return v

    @field_validator("errors")
    @classmethod
    def check_errors_format(cls, v: list[str]):
        if not isinstance(v, list):
            raise ValueError("Errors must be a list of strings")
        return v
