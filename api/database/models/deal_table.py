from uuid import uuid4, UUID
from time import time
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING

# avoids circular imports
if TYPE_CHECKING:
    from database.models.bot_table import BotTable, PaperTradingTable


class DealBase(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    buy_price: float = Field(default=0)
    buy_total_qty: float = Field(default=0)
    buy_timestamp: float = time() * 1000
    current_price: float = Field(default=0)
    sd: float = Field(default=0)
    avg_buy_price: float = Field(default=0)
    take_profit_price: float = Field(default=0)
    sell_timestamp: float = Field(default=0)
    sell_price: float = Field(default=0)
    sell_qty: float = Field(default=0)
    trailling_stop_loss_price: float = Field(default=0)
    # take_profit but for trailling, to avoid confusion, trailling_profit_price always be > trailling_stop_loss_price
    trailling_profit_price: float = Field(default=0)
    stop_loss_price: float = Field(default=0)
    trailling_profit: float = Field(default=0)
    so_prices: float = Field(default=0)
    post_closure_current_price: float = Field(default=0)
    original_buy_price: float = Field(
        default=0
    )  # historical buy_price after so trigger
    short_sell_price: float = Field(default=0)
    short_sell_qty: float = Field(default=0)
    short_sell_timestamp: float = time() * 1000

    # fields for margin trading
    margin_short_loan_principal: float = Field(default=0)
    margin_loan_id: float = Field(default=0)
    hourly_interest_rate: float = Field(default=0)
    margin_short_sell_price: float = Field(default=0)
    margin_short_loan_interest: float = Field(default=0)
    margin_short_buy_back_price: float = Field(default=0)
    margin_short_sell_qty: float = Field(default=0)
    margin_short_buy_back_timestamp: int = Field(default=0)
    margin_short_base_order: float = Field(default=0)
    margin_short_sell_timestamp: int = Field(default=0)
    margin_short_loan_timestamp: int = Field(default=0)

    # Relationships
    # bot_id: Optional[UUID] = Field(default=None, foreign_key="bot.id")
    # paper_trading_id: Optional[UUID] = Field(default=None, foreign_key="paper_trading.id")


class DealTable(DealBase, table=True):
    """
    Data model that is used for operations,
    so it should all be numbers (int or float)
    """

    __tablename__ = "deal"

    # Relationships
    bot_id: Optional[UUID] = Field(default=None, foreign_key="bot.id")
    paper_trading_id: Optional[UUID] = Field(
        default=None, foreign_key="paper_trading.id"
    )
    bot: Optional["BotTable"] = Relationship(back_populates="deal")
    paper_trading: Optional["PaperTradingTable"] = Relationship(back_populates="deal")
    pass
