from uuid import UUID, uuid4

from pybinbot import BotBase, OrderBase
from pybinbot import DealBase as DealModel
from pydantic import BaseModel, Field, field_validator

from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.tables.deal_table import DealTable
from databases.tables.order_table import ExchangeOrderTable
from tools.handle_error import IResponseBase


class OrderModel(OrderBase):
    @classmethod
    def dump_from_table(cls, bot):
        """
        Same as model_dump() but from
        BotTable
        """
        if isinstance(bot, BotTable) or isinstance(bot, PaperTradingTable):
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


class BotModel(BotBase):
    """
    The way SQLModel works causes a lot of errors
    if we combine (with inheritance) both Pydantic models
    and SQLModels. they are not compatible. Thus the duplication
    """

    id: UUID | None = Field(default_factory=uuid4)
    deal: DealModel = Field(default_factory=DealModel)
    orders: list[OrderModel] = Field(default=[])

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
        "json_schema_extra": {
            "description": "BotModel with id, deal, and orders. Deal and orders fields are generated internally and filled by Exchange",
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "pair": "BNBUSDT",
                    "fiat": "USDC",
                    "quote_asset": "USDC",
                    "fiat_order_size": 15,
                    "candlestick_interval": "15m",
                    "close_condition": "dynamic_trailling",
                    "cooldown": 0,
                    "created_at": 1702999999.0,
                    "updated_at": 1702999999.0,
                    "dynamic_trailling": False,
                    "logs": [],
                    "mode": "manual",
                    "name": "Default bot",
                    "status": "inactive",
                    "stop_loss": 0,
                    "take_profit": 2.3,
                    "trailling": True,
                    "trailling_deviation": 0.63,
                    "trailling_profit": 2.3,
                    "margin_short_reversal": False,
                    "strategy": "long",
                    "deal": {},
                    "orders": [],
                }
            ],
        },
    }

    @field_validator("id")
    @classmethod
    def deserialize_id(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    @classmethod
    def dump_from_table(cls, bot):
        """
        Same as model_dump() but from
        BotTable
        """
        if isinstance(bot, BotTable) or isinstance(bot, PaperTradingTable):
            model = BotModel.model_construct(**bot.model_dump())
            if not bot.deal.base_order_size:
                bot.deal.base_order_size = 0
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
    orders: list[OrderModel] = Field(default=[])

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
        "json_schema_extra": {
            "description": "API response model with id, deal, and orders. Deal and orders fields are populated by the system",
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "pair": "BNBUSDT",
                    "fiat": "USDC",
                    "quote_asset": "USDC",
                    "fiat_order_size": 15,
                    "candlestick_interval": "15m",
                    "close_condition": "dynamic_trailling",
                    "cooldown": 0,
                    "created_at": 1702999999.0,
                    "updated_at": 1702999999.0,
                    "dynamic_trailling": False,
                    "logs": [],
                    "mode": "manual",
                    "name": "Default bot",
                    "status": "inactive",
                    "stop_loss": 0,
                    "take_profit": 2.3,
                    "trailling": True,
                    "trailling_deviation": 0.63,
                    "trailling_profit": 2.3,
                    "margin_short_reversal": False,
                    "strategy": "long",
                    "deal": {},
                    "orders": [],
                }
            ],
        },
    }

    @field_validator("id", mode="before")
    def deserialize_id(cls, v):
        if isinstance(v, UUID):
            cls.id = str(v)
            return str(v)
        return v

    @classmethod
    def dump_from_table(cls, bot):
        """
        Same as model_dump() but from
        BotTable

        Use model_validate to cast/pre-validate data to avoid unecessary validation errors
        """
        if isinstance(bot, BotTable) or isinstance(bot, PaperTradingTable):
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
    data: BotModelResponse | None = Field(default=None)


class BotPairsList(IResponseBase):
    data: list = Field(default=[])


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
