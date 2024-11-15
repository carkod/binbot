from uuid import uuid4, UUID
from time import time
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import JSON, Column, Enum
from tools.enum_definitions import (
    BinanceKlineIntervals,
    CloseConditions,
    Status,
    Strategy,
)
from sqlmodel import Relationship, SQLModel, Field

# avoids circular imports
# https://sqlmodel.tiangolo.com/tutorial/code-structure/#hero-model-file
if TYPE_CHECKING:
    from database.models.deal_table import DealTable
    from database.models.order_table import ExchangeOrderTable


class BotTable(SQLModel, table=True):

    __tablename__ = "bot"

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False
    )
    pair: str = Field(index=True)
    fiat: str = Field(default="USDC")
    # Min Binance 0.0001 BNB
    base_order_size: float = Field(default=15)
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
        sa_column=Column(Enum(CloseConditions)),
    )
    # cooldown period in minutes before opening next bot with same pair
    cooldown: int = Field(default=0)
    created_at: float = Field(default_factory=lambda: time() * 1000)
    deal: Optional["DealTable"] = Relationship(back_populates="bot")
    dynamic_trailling: bool = Field(default=False)
    logs: JSON = Field(default="[]", sa_column=Column(JSON))
    mode: str = Field(default="manual")
    name: str = Field(default="Default bot")
    # filled up internally
    orders: Optional[List["ExchangeOrderTable"]] = Relationship(back_populates="bot")
    status: str = Field(default=Status.inactive, sa_column=Column(Enum(Status)))
    stop_loss: float = Field(default=0, gt=0)
    # If stop_loss > 0, allow for reversal
    margin_short_reversal: bool = Field(default=False)
    take_profit: float = Field(default=0, gt=0)
    trailling: bool = Field(default=False)
    trailling_deviation: float = Field(default=0, gt=0)
    # Trailling activation (first take profit hit)
    trailling_profit: float = Field(default=0, gt=0)
    strategy: str = Field(default=Strategy.long, sa_column=Column(Enum(Strategy)))
    short_buy_price: float = Field(default=0)
    # autoswitch to short_strategy
    short_sell_price: float = Field(default=0)
    total_commission: float = Field(default=0)
    updated_at: float = Field(default_factory=lambda: time() * 1000)

    class Config:
        arbitrary_types_allowed = True
