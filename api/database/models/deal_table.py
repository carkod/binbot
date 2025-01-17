from uuid import uuid4, UUID
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, BigInteger

# avoids circular imports
if TYPE_CHECKING:
    from database.models.bot_table import BotTable, PaperTradingTable


class DealBase(SQLModel):
    buy_price: float = Field(default=0)
    buy_total_qty: float = Field(default=0)
    buy_timestamp: float = Field(
        default=0,
        description="Deal timestamps in general should be set by the moment deal action happens, so no default values",
        sa_column=Column(BigInteger()),
    )
    current_price: float = Field(default=0)
    sd: float = Field(default=0)
    avg_buy_price: float = Field(default=0)
    take_profit_price: float = Field(default=0)
    sell_timestamp: float = Field(default=0, sa_column=Column(BigInteger()))
    sell_price: float = Field(default=0)
    sell_qty: float = Field(default=0)
    trailling_stop_loss_price: float = Field(
        default=0,
        description="take_profit but for trailling, to avoid confusion, trailling_profit_price always be > trailling_stop_loss_price",
    )
    trailling_profit_price: float = Field(default=0)
    stop_loss_price: float = Field(default=0)
    trailling_profit: float = Field(default=0)
    original_buy_price: float = Field(default=0)

    # fields for margin trading
    margin_short_loan_principal: float = Field(default=0)
    margin_loan_id: float = Field(default=0)
    hourly_interest_rate: float = Field(default=0, sa_column=Column(BigInteger()))
    margin_short_sell_price: float = Field(default=0)
    margin_short_loan_interest: float = Field(default=0)
    margin_short_buy_back_price: float = Field(default=0)
    margin_short_sell_qty: float = Field(default=0)
    margin_short_buy_back_timestamp: int = Field(
        default=0, sa_column=Column(BigInteger())
    )
    margin_short_base_order: float = Field(
        default=0, description="To be merged with base_order"
    )
    margin_short_sell_timestamp: int = Field(default=0, sa_column=Column(BigInteger()))
    margin_short_loan_timestamp: int = Field(default=0, sa_column=Column(BigInteger()))

    # Refactored deal prices that combine both margin and spot
    opening_price: Optional[float] = Field(
        default=0,
        description="replaces previous buy_price or short_sell_price/margin_short_sell_price",
    )
    opening_qty: Optional[float] = Field(
        default=0,
        description="replaces previous buy_total_qty or short_sell_qty/margin_short_sell_qty",
    )
    opening_timestamp: Optional[int] = Field(default=0, sa_column=Column(BigInteger()))
    closing_price: Optional[float] = Field(
        default=0,
        description="replaces previous sell_price or short_sell_price/margin_short_sell_price",
    )
    closing_qty: Optional[float] = Field(
        default=0,
        description="replaces previous sell_qty or short_sell_qty/margin_short_sell_qty",
    )
    closing_timestamp: Optional[int] = Field(
        default=0,
        description="replaces previous buy_timestamp or margin/short_sell timestamps",
        sa_column=Column(BigInteger()),
    )


class DealTable(DealBase, table=True):
    """
    Data model that is used for operations,
    so it should all be numbers (int or float)
    """

    __tablename__ = "deal"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Relationships
    bot: Optional["BotTable"] = Relationship(back_populates="deal", cascade_delete=True)
    paper_trading: Optional["PaperTradingTable"] = Relationship(
        back_populates="deal",
        cascade_delete=True,
        sa_relationship_kwargs={"viewonly": True},
    )
