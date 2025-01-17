from uuid import uuid4, UUID
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, BigInteger

# avoids circular imports
if TYPE_CHECKING:
    from database.models.bot_table import BotTable, PaperTradingTable


class DealBase(SQLModel):
    current_price: float = Field(default=0)
    take_profit_price: float = Field(default=0, description="derived from take_profit, while this price gets updated according to market, take_profit percentage doesn't")
    trailling_stop_loss_price: float = Field(
        default=0,
        description="take_profit but for trailling, to avoid confusion, trailling_profit_price always be > trailling_stop_loss_price",
    )
    trailling_profit_price: float = Field(default=0)
    stop_loss_price: float = Field(default=0)

    # fields for margin trading
    total_interests: float = Field(default=0, gt=-1)
    total_commissions: float = Field(default=0, gt=-1)
    margin_loan_id: float = Field(default=0)

    # Refactored deal prices that combine both margin and spot
    opening_price: float = Field(
        default=0,
        description="buy price (long spot) or short sell price (short margin trading)",
    )
    opening_qty: float = Field(
        default=0,
        description="buy quantity (long spot) or short sell quantity (short margin trading)",
    )
    opening_timestamp: int = Field(default=0, sa_column=Column(BigInteger()))
    closing_price: float = Field(
        default=0,
        description="sell price (long spot) or buy back price (short margin trading)",
    )
    closing_qty: float = Field(
        default=0,
        description="sell quantity (long spot) or buy back quantity (short margin trading)",
    )
    closing_timestamp: int = Field(
        default=0,
        sa_column=Column(BigInteger()),
    )


class DealTable(DealBase, table=True):
    """
    Data model that is used for operations,
    so it should all be numbers (int or float)
    """

    __tablename__ = "deal"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, unique=True)

    # Relationships
    bot: Optional["BotTable"] = Relationship(back_populates="deal", cascade_delete=True)
    paper_trading: Optional["PaperTradingTable"] = Relationship(
        back_populates="deal",
        cascade_delete=True,
        sa_relationship_kwargs={"viewonly": True},
    )
