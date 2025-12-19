from typing import List, Optional
from uuid import uuid4, UUID
from tools.enum_definitions import (
    QuoteAssets,
    BinanceKlineIntervals,
    CloseConditions,
    Status,
    Strategy,
)
from deals.models import DealModel
from pydantic import BaseModel, Field, field_validator
from databases.utils import timestamp
from tools.handle_error import IResponseBase
from tools.enum_definitions import DealType, OrderStatus
from tools.maths import ts_to_humandate
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.tables.deal_table import DealTable
from databases.tables.order_table import ExchangeOrderTable
from databases.utils import Amount


class OrderModel(BaseModel):
    order_type: str = Field(
        description="Because every exchange has different naming, we should keep it as a str rather than OrderType enum"
    )
    time_in_force: str
    timestamp: int = Field(default=0)
    order_id: int | str = Field(
        description="Because every exchange has id type, we should keep it as looose as possible. Int is for backwards compatibility"
    )
    order_side: str = Field(
        description="Because every exchange has different naming, we should keep it as a str rather than OrderType enum"
    )
    pair: str
    qty: float
    status: OrderStatus
    price: float
    deal_type: DealType

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
        "json_schema_extra": {
            "description": "Most fields are optional. Deal field is generated internally, orders are filled up by Exchange",
            "examples": [
                {
                    "order_type": "LIMIT",
                    "time_in_force": "GTC",
                    "timestamp": 0,
                    "order_id": 0,
                    "order_side": "BUY",
                    "pair": "",
                    "qty": 0,
                    "status": "",
                    "price": 0,
                }
            ],
        },
    }

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


class BotBase(BaseModel):
    pair: str
    fiat: str = Field(default="USDC")
    quote_asset: QuoteAssets = Field(default=QuoteAssets.USDC)
    fiat_order_size: Amount = Field(
        default=0, ge=0, description="Min Binance 0.0001 BNB approx 15USD"
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
    name: str = Field(
        default="terminal",
        description="Algorithm name or 'terminal' if executed from React app",
    )
    status: Status = Field(default=Status.inactive)
    stop_loss: Amount = Field(
        default=0,
        ge=-1,
        le=101,
        description="If stop_loss > 0, allow for reversal",
    )
    margin_short_reversal: bool = Field(
        default=False,
        description="Autoswitch from long to short or short to long strategy",
    )
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

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
        "json_schema_extra": {
            "description": "Most fields are optional. Deal and orders fields are generated internally and filled by Exchange",
            "examples": [
                {
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
                }
            ],
        },
    }

    @field_validator("pair")
    @classmethod
    def check_pair_not_empty(cls, v):
        assert v != "", "Pair field must be filled."
        return v

    def add_log(self, message: str) -> str:
        """Convenience helper for adding a single log entry.

        Returns the formatted log string (with timestamp) for immediate reuse/testing.
        """
        timestamped_message = f"[{ts_to_humandate(timestamp())}] {message}"
        self.logs.append(timestamped_message)
        return self.logs[-1]


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
    orders: List[OrderModel] = Field(default=[])

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
    data: Optional[BotModelResponse] = Field(default=None)


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
