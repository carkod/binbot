from uuid import uuid4, UUID
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, BigInteger, Float
from pydantic import field_validator

# avoids circular imports
if TYPE_CHECKING:
    from database.models.bot_table import BotTable, PaperTradingTable


class DealBase(SQLModel):
    current_price: float = Field(default=0)
    take_profit_price: float = Field(
        default=0,
        description="derived from take_profit, while this price gets updated according to market, take_profit percentage doesn't",
    )
    trailling_stop_loss_price: float = Field(
        default=0,
        description="take_profit but for trailling, to avoid confusion, trailling_profit_price always be > trailling_stop_loss_price, and it cannot be triggered unless it's above opening_price",
    )
    trailling_profit_price: float = Field(default=0)
    stop_loss_price: float = Field(default=0)

    # fields for margin trading
    total_interests: float = Field(default=0, gt=-1, sa_column=Column(Float()))
    total_commissions: float = Field(default=0, gt=-1, sa_column=Column(Float()))
    margin_loan_id: int = Field(
        default=0,
        description="Txid from Binance. This is used to check if there is a loan, 0 means no loan",
        sa_column=Column(BigInteger()),
    )
    margin_repay_id: int = Field(
        default=0,
        gt=-1,
        description="= 0, it has not been repaid",
        sa_column=Column(BigInteger()),
    )

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

    @field_validator("margin_loan_id", mode="before")
    @classmethod
    def validate_margin_loan_id(cls, value):
        if isinstance(value, float):
            return int(value)

    @field_validator("margin_loan_id", mode="after")
    @classmethod
    def cast_float(cls, value):
        if isinstance(value, float):
            return int(value)
