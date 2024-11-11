from time import time
from typing import Literal

from bson.objectid import ObjectId
from deals.models import BinanceOrderModel, DealModel
from tools.enum_definitions import BinanceKlineIntervals, CloseConditions, Status
from pydantic import BaseModel, Field, field_validator
from tools.handle_error import StandardResponse
from tools.enum_definitions import BinbotEnums


class SafetyOrderSchema(BaseModel):
    name: str = "so_1"  # should be so_<index>
    status: Literal[0, 1, 2] = (
        0  # 0 = standby, safety order hasn't triggered, 1 = filled safety order triggered, 2 = error
    )
    order_id: str | None = None
    created_at: float = time() * 1000
    updated_at: float = time() * 1000
    buy_price: float = 0  # base currency quantity e.g. 3000 USDC in BTCUSDT
    buy_timestamp: float = 0
    so_size: float = 0  # quote currency quantity e.g. 0.00003 BTC in BTCUSDT
    max_active_so: float = 0
    so_volume_scale: float = 0
    so_step_scale: float = 0
    so_asset: str = "USDC"
    errors: list[str] = []
    total_commission: float = 0


class BotSchema(BaseModel):
    id: str | None = ""
    pair: str
    balance_size_to_use: str | float = 1
    balance_to_use: str | float = "1"
    base_order_size: str | float = "15"  # Min Binance 0.0001 BNB
    candlestick_interval: BinanceKlineIntervals = BinanceKlineIntervals.fifteen_minutes
    close_condition: CloseConditions = CloseConditions.dynamic_trailling
    cooldown: int = (
        0  # cooldown period in minutes before opening next bot with same pair
    )
    created_at: float = time() * 1000
    deal: DealModel = Field(default_factory=DealModel)
    dynamic_trailling: bool = False
    errors: list[str] = []  # Event logs
    locked_so_funds: float = 0  # funds locked by Safety orders
    mode: str = "manual"
    name: str = "Default bot"
    orders: list[BinanceOrderModel] = []  # Internal
    status: Status = Status.inactive
    stop_loss: float = 0
    margin_short_reversal: bool = False  # If stop_loss > 0, allow for reversal
    take_profit: float = 0
    trailling: bool = True
    trailling_deviation: float = 0
    trailling_profit: float = 0  # Trailling activation (first take profit hit)
    strategy: str = "long"
    short_buy_price: float = 0
    short_sell_price: float = 0  # autoswitch to short_strategy
    # Deal and orders are internal, should never be updated by outside data
    total_commission: float = 0
    updated_at: float = time() * 1000

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "description": "Most fields are optional. Deal field is generated internally, orders are filled up by Binance",
            "examples": [
                {
                    "pair": "BNBUSDT",
                    "balance_size_to_use": "0",
                    "balance_to_use": "USDC",
                    "base_order_size": "15",
                    "candlestick_interval": "15m",
                    "cooldown": 0,
                    "errors": [],
                    "locked_so_funds": 0,
                    "mode": "manual",  # Manual is triggered by the terminal dashboard, autotrade by research app,
                    "name": "Default bot",
                    "orders": [],
                    "status": "inactive",
                    "stop_loss": 0,
                    "take_profit": 2.3,
                    "trailling": "true",
                    "trailling_deviation": 0.63,
                    "trailling_profit": 2.3,
                    "safety_orders": [],
                    "strategy": "long",
                    "short_buy_price": 0,
                    "short_sell_price": 0,
                    "total_commission": 0,
                }
            ],
        },
    }

    @field_validator("pair", "base_order_size", "candlestick_interval")
    @classmethod
    def check_names_not_empty(cls, v):
        assert v != "", "Empty pair field."
        return v

    @field_validator("balance_size_to_use", "base_order_size")
    @classmethod
    def validate_str_numbers(cls, v):
        if isinstance(v, float):
            return str(v)
        elif isinstance(v, int):
            return str(v)
        else:
            return v

    @field_validator(
        "stop_loss", "take_profit", "trailling_deviation", "trailling_profit"
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
    def check_trailling(cls, v: str | bool):
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


class BotListResponse(StandardResponse):
    data: list[BotSchema]


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
