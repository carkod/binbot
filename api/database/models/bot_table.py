from time import time
from database.models.deal_table import DealTable
from binquant.shared.enums import Strategy
from tools.enum_definitions import (
    BinanceKlineIntervals,
    CloseConditions,
    Status,
)
from sqlmodel import SQLModel, Field, Relationship


class BotTable(SQLModel, table=True):
    id: str | None = Field(default=None, primary_key=True)
    pair: str = Field(index=True)
    balance_size_to_use: str | float = Field(default=1)
    balance_to_use: str | float = Field(default=1)
    # Min Binance 0.0001 BNB
    base_order_size: str | float = Field(default=15)
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes
    )
    close_condition: CloseConditions = Field(default=CloseConditions.dynamic_trailling)
    # cooldown period in minutes before opening next bot with same pair
    cooldown: int = Field(default=0)
    created_at: float = Field(default_factory=lambda: time() * 1000)
    deal_id: int = Field(foreign_key="deal.id")
    deal: DealTable = Relationship(back_populates="bot", cascade_delete=True)
    dynamic_trailling: bool = Field(default=False)
    # Event logs
    errors: list[str] = Field(default_factory=list)
    mode: str = Field(default="manual")
    name: str = Field(default="Default bot")
    # Internal
    orders_id: list[int] = Field(foreign_key="ExchangeOrderTable.id", default_factory=list)
    status: Status = Field(default=Status.inactive)
    stop_loss: float = Field(default=0)
    # If stop_loss > 0, allow for reversal
    margin_short_reversal: bool = Field(default=False)
    take_profit: float = Field(default=0)
    trailling: bool = Field(default=True)
    trailling_deviation: float = Field(default=0)
    # Trailling activation (first take profit hit)
    trailling_profit: float = Field(default=0)
    strategy: str = Field(default=Strategy.long)
    short_buy_price: float = Field(default=0)
    # autoswitch to short_strategy
    short_sell_price: float = Field(default=0)
    total_commission: float = Field(default=0)
    updated_at: float = Field(default_factory=lambda: time() * 1000)
