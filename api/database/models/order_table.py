from typing import Optional
from uuid import UUID

from pydantic import ValidationInfo, field_validator
from sqlalchemy import Column, Enum
from database.models.paper_trading_table import PaperTradingTable
from database.models.bot_table import BotTable
from tools.enum_definitions import DealType
from sqlmodel import Field, Relationship, SQLModel


class ExchangeOrderTable(SQLModel, table=True):
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
    order_type: str = Field(nullable=True)
    time_in_force: str = Field(nullable=True)
    timestamp: int = Field(nullable=True)
    order_side: str = Field(nullable=True)
    pair: str = Field(nullable=True)
    qty: float = Field(nullable=True)
    status: str = Field(nullable=True)
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
