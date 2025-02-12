from typing import List, Optional
from uuid import uuid4, UUID
from tools.enum_definitions import (
    BinanceKlineIntervals,
    CloseConditions,
    Status,
    Strategy,
)
from deals.models import DealModel
from pydantic import BaseModel, Field, field_validator
from database.utils import timestamp
from tools.handle_error import IResponseBase
from tools.enum_definitions import DealType, OrderType
from database.models.bot_table import BotTable
from database.models.deal_table import DealTable
from database.models.order_table import ExchangeOrderTable
from database.utils import Amount


class OrderModel(BaseModel):
    order_type: OrderType
    time_in_force: str
    timestamp: int = Field(default=0)
    order_id: int
    order_side: str
    pair: str
    qty: float
    status: str
    price: float
    deal_type: DealType

    @classmethod
    def dump_from_table(cls, bot):
        """
        Same as model_dump() but from
        BotTable
        """
        if isinstance(bot, BotTable):
            model = BotModel.model_construct(**bot.model_dump())
            deal_model = DealModel.model_construct(**bot.deal.model_dump())
            order_models = [
                OrderModel.model_construct(**order.model_dump()) for order in bot.orders
            ]
            model.deal = deal_model
            model.orders = order_models
            return model
        else:
            return bot


class BotBase(BaseModel):
    pair: str
    fiat: str = Field(default="USDC")
    base_order_size: Amount = Field(
        default=15, ge=0, description="Min Binance 0.0001 BNB approx 15USD"
    )
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
    )
    cooldown: int = Field(
        default=0,
        ge=0,
        description="cooldown period in minutes before opening next bot with same pair",
    )
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
    dynamic_trailling: bool = Field(default=False)
    logs: list = Field(default=[])
    mode: str = Field(default="manual")
    name: str = Field(default="Default bot")
    status: Status = Field(default=Status.inactive)
    stop_loss: Amount = Field(
        default=0,
        ge=-1,
        le=101,
        description="If stop_loss > 0, allow for reversal",
    )
    margin_short_reversal: bool = Field(default=False)
    take_profit: Amount = Field(default=0, ge=-1, le=101)
    trailling: bool = Field(default=False)
    trailling_deviation: Amount = Field(
        default=0,
        ge=-1,
        le=101,
        description="Trailling activation (first take profit hit)",
    )
    trailling_profit: Amount = Field(default=0, ge=-1, le=101)
    strategy: Strategy = Field(default=Strategy.long)


class BotModel(BotBase):
    """
    The way SQLModel works causes a lot of errors
    if we combine (with inheritance) both Pydantic models
    and SQLModels. they are not compatible. Thus the duplication
    """

    id: Optional[UUID] = Field(default_factory=uuid4)
    deal: DealModel = Field(default_factory=DealModel)
    orders: List[OrderModel] = Field(default=[])

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
                    "trailling": True,
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

    @field_validator("id")
    def deserialize_id(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return True

    @classmethod
    def dump_from_table(cls, bot):
        """
        Same as model_dump() but from
        BotTable
        """
        if isinstance(bot, BotTable):
            model = BotModel.model_construct(**bot.model_dump())
            deal_model = DealModel.model_validate(bot.deal.model_dump())
            order_models = [
                OrderModel.model_construct(**order.model_dump()) for order in bot.orders
            ]
            model.deal = deal_model
            model.orders = order_models
            return model
        else:
            return bot

    @classmethod
    def model_to_table(cls, bot):
        """
        Same as model_dump() but from
        BotModel to BotTable
        """
        if isinstance(cls, BotModel):
            model = BotTable.model_construct(**cls.model_dump())
            deal_model = DealTable.model_construct(**cls.deal.model_dump())
            order_models = [
                ExchangeOrderTable.model_construct(**order.model_dump())
                for order in cls.orders
            ]
            model.deal = deal_model
            model.orders = order_models
            return model
        else:
            return bot


class BotModelResponse(BotBase):
    id: str = Field(default="")
    deal: DealModel = Field(...)
    orders: List[OrderModel] = Field(default=[])

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
                    "trailling": True,
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

    @field_validator("id", mode="before")
    def deserialize_id(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return True

    @classmethod
    def dump_from_table(cls, bot):
        """
        Same as model_dump() but from
        BotTable

        Use model_validate to cast/pre-validate data to avoid unecessary validation errors
        """
        if isinstance(bot, BotTable):
            model = BotModelResponse.model_construct(**bot.model_dump())
            deal_model = DealModel.model_validate(bot.deal.model_dump())
            order_models = [
                OrderModel.model_validate(order.model_dump()) for order in bot.orders
            ]
            model.deal = deal_model
            model.orders = order_models
            return model
        else:
            return bot


class BotDataErrorResponse(BotBase):
    error: str


class BotResponse(IResponseBase):
    data: Optional[BotModelResponse] = Field(default=None)


class BotListResponse(IResponseBase):
    """
    Model exclusively used to serialize
    list of bots.

    Has to be converted to BotModel to be able to
    serialize nested table objects (deal, orders)
    """

    data: list = Field(default=[])


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
