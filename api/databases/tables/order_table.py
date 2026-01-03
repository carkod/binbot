from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from pybinbot import DealType, OrderStatus
from pydantic import ValidationInfo, field_validator
from sqlalchemy import BigInteger, Column
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from databases.tables.bot_table import BotTable, PaperTradingTable


class OrderTableBase(SQLModel):
    order_type: str = Field(
        description="Because every exchange has different naming, we should keep it as a str rather than OrderType enum"
    )
    time_in_force: str
    order_id: str = Field(nullable=False, description="For fake orders use -1")
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


class ExchangeOrderTable(OrderTableBase, table=True):
    """
    Data provided by Crypto Exchange,
    therefore they should be all be strings

    This should be an immutable source of truth
    whatever shape comes from third party provider,
    should be stored the same way

    id: orderId from Exchange
    """

    __tablename__ = "exchange_order"

    id: UUID = Field(
        primary_key=True, default_factory=uuid4, nullable=False, unique=True, index=True
    )

    timestamp: int = Field(sa_column=Column(BigInteger()))

    # Relationships
    bot_id: UUID | None = Field(
        default=None, foreign_key="bot.id", ondelete="CASCADE", index=True
    )
    bot: Optional["BotTable"] = Relationship(back_populates="orders")

    @field_validator("price", "qty")
    @classmethod
    def validate_str_numbers(cls, v, info: ValidationInfo):
        if isinstance(v, str):
            return float(v)
        elif isinstance(v, int):
            return float(v)
        elif isinstance(v, float):
            return v
        else:
            raise ValueError(f"{info.field_name} must be float")

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v, info: ValidationInfo):
        if isinstance(v, str):
            return v
        elif isinstance(v, int):
            return str(v)
        else:
            raise ValueError(f"{info.field_name} must be str or int")


class FakeOrderTable(OrderTableBase, table=True):
    """
    Fake orders for paper trading
    """

    __tablename__ = "fake_order"

    id: UUID = Field(
        primary_key=True, default_factory=uuid4, nullable=False, unique=True, index=True
    )

    timestamp: int = Field(sa_column=Column(BigInteger()))

    # Relationships
    paper_trading_id: UUID | None = Field(
        default=None, foreign_key="paper_trading.id", ondelete="CASCADE", index=True
    )
    paper_trading: Optional["PaperTradingTable"] = Relationship(back_populates="orders")
