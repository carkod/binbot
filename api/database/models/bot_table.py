from uuid import uuid4, UUID
from typing import TYPE_CHECKING, Optional, List
from pydantic import Json, field_validator
from sqlalchemy import JSON, Column, Enum
from database.utils import timestamp
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
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    pair: str = Field(index=True)
    fiat: str = Field(default="USDC", index=True)
    base_order_size: float = Field(
        default=15, description="Min Binance 0.0001 BNB approx 15USD"
    )
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
        sa_column=Column(Enum(CloseConditions)),
    )
    cooldown: int = Field(
        default=0,
        description="cooldown period in minutes before opening next bot with same pair",
    )
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
    dynamic_trailling: bool = Field(default=False)
    logs: List[str] = Field(default=[], sa_column=Column(JSON))
    mode: str = Field(default="manual")
    name: str = Field(default="Default bot")
    status: Status = Field(default=Status.inactive, sa_column=Column(Enum(Status)))
    stop_loss: float = Field(
        default=0, description="If stop_loss > 0, allow for reversal"
    )
    margin_short_reversal: bool = Field(default=False)
    take_profit: float = Field(default=0)
    trailling: bool = Field(default=False)
    trailling_deviation: float = Field(
        default=0,
        ge=-1,
        le=101,
        description="Trailling activation (first take profit hit)",
    )
    trailling_profit: float = Field(default=0)
    strategy: Strategy = Field(default=Strategy.long, sa_column=Column(Enum(Strategy)))
    total_commission: float = Field(
        default=0, description="autoswitch to short_strategy"
    )

    # Table relationships filled up internally
    orders: Optional[list["ExchangeOrderTable"]] = Relationship(back_populates="bot")
    deal: Optional["DealTable"] = Relationship(back_populates="bot")

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
    }

    @field_validator("logs", mode="before")
    def validate_logs(cls, v, info):
        return v


class PaperTradingTable(SQLModel, table=True):
    """
    Fake bots

    these trade without actual money, so qty
    is usually 0 or 1. Orders are simulated

    This cannot inherit from a SQLModel base
    because errors with candlestick_interval
    already assigned to BotTable error
    """

    __tablename__ = "paper_trading"

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    pair: str = Field(index=True)
    fiat: str = Field(default="USDC", index=True)
    base_order_size: float = Field(
        default=15, description="Min Binance 0.0001 BNB approx 15USD"
    )
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailling,
        sa_column=Column(Enum(CloseConditions)),
    )
    cooldown: int = Field(
        default=0,
        description="cooldown period in minutes before opening next bot with same pair",
    )
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
    dynamic_trailling: bool = Field(default=False)
    logs: list[Json[str]] = Field(default=[], sa_column=Column(JSON))
    mode: str = Field(default="manual")
    name: str = Field(default="Default bot")
    status: Status = Field(default=Status.inactive, sa_column=Column(Enum(Status)))
    stop_loss: float = Field(
        default=0, description="If stop_loss > 0, allow for reversal"
    )
    margin_short_reversal: bool = Field(default=False)
    take_profit: float = Field(default=0)
    trailling: bool = Field(default=False)
    trailling_deviation: float = Field(
        default=0,
        ge=-1,
        le=101,
        description="Trailling activation (first take profit hit)",
    )
    trailling_profit: float = Field(default=0)
    strategy: Strategy = Field(default=Strategy.long, sa_column=Column(Enum(Strategy)))
    short_buy_price: float = Field(
        default=0, description="autoswitch to short_strategy"
    )
    short_sell_price: float = Field(
        default=0, description="autoswitch to short_strategy"
    )
    total_commission: float = Field(
        default=0, description="autoswitch to short_strategy"
    )

    # Table relationships filled up internally
    deal: "DealTable" = Relationship(back_populates="paper_trading")
    orders: Optional[list["ExchangeOrderTable"]] = Relationship(
        back_populates="paper_trading"
    )

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
    }
