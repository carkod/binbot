from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import ValidationInfo, field_validator
from sqlalchemy import Column, Enum
from tools.enum_definitions import DealType, OrderType
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from database.models.bot_table import BotTable
    from database.models.paper_trading_table import PaperTradingTable


class OrderModel(SQLModel):
    order_type: OrderType
    time_in_force: str
    timestamp: Optional[int]
    order_id: int = Field(nullable=True)
    order_side: str
    pair: str
    qty: float
    status: str
    price: float
    deal_type: DealType


class ExchangeOrderTable(OrderModel, table=True):
    """
    Data provided by Crypto Exchange,
    therefore they should be all be strings

    This should be an immutable source of truth
    whatever shape comes from third party provider,
    should be stored the same way

    id: orderId from Exchange
    """

    __tablename__ = "exchange_order"

    id: int = Field(primary_key=True)
    price: float = Field(nullable=True)
    deal_type: DealType = Field(sa_column=Column(Enum(DealType)))
    total_commission: float = Field(nullable=True, default=0)

    # Relationships
    bot_id: Optional[UUID] = Field(default=None, foreign_key="bot.id")
    bot: Optional["BotTable"] = Relationship(back_populates="orders")
    paper_trading_id: Optional[UUID] = Field(
        default=None, foreign_key="paper_trading.id"
    )
    paper_trading: Optional["PaperTradingTable"] = Relationship(back_populates="orders")

    @field_validator("price", "qty", mode="before")
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
