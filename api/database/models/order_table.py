from typing import TYPE_CHECKING, Optional
from pydantic import ValidationInfo, field_validator
from sqlalchemy import Column, Enum
from tools.enum_definitions import DealType, OrderType
from sqlmodel import Field, Relationship, SQLModel
from uuid import UUID, uuid4


if TYPE_CHECKING:
    from database.models.bot_table import BotTable, PaperTradingTable


class OrderBase(SQLModel):
    order_type: OrderType
    time_in_force: str
    timestamp: Optional[int]
    order_id: int = Field(nullable=False)
    order_side: str
    pair: str
    qty: float
    status: str
    price: float
    deal_type: DealType

    # Relationships
    bot_id: Optional[UUID] = Field(default=None, foreign_key="bot.id")
    paper_trading_id: Optional[UUID] = Field(
        default=None, foreign_key="paper_trading.id"
    )

    model_config = {
        "use_enum_values": True,
    }


class ExchangeOrderTable(OrderBase, table=True):
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
    price: float = Field(nullable=True)
    deal_type: DealType = Field(sa_column=Column(Enum(DealType)))
    total_commission: float = Field(nullable=True, default=0)

    # Relationships
    bot: Optional["BotTable"] = Relationship(back_populates="orders")
    paper_trading: Optional["PaperTradingTable"] = Relationship(back_populates="orders")

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
