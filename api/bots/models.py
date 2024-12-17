from typing import List
from database.models.order_table import ExchangeOrderTable
from deals.models import DealModel
from database.models.bot_table import BotBase, BotTable
from pydantic import BaseModel, Field, field_validator

from tools.handle_error import StandardResponse


class BotModel(BotBase):
    deal: DealModel = Field(default_factory=DealModel)
    orders: List[ExchangeOrderTable] = Field(default=[])

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
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


class BotResponse(StandardResponse):
    data: BotModel


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


class GetBotParams(BaseModel):
    status: str | None = None
    start_date: float | None = None
    end_date: float | None = None
    no_cooldown: bool = True
    limit: int = 100
    offset: int = 0
