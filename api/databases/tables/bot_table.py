from uuid import uuid4, UUID
from typing import TYPE_CHECKING, Optional
from pydantic import field_validator
from sqlalchemy import JSON, Column, Enum
from pybinbot import (
    QuoteAssets,
    BinanceKlineIntervals,
    Status,
    timestamp,
    MarketType,
    CloseConditions,
    Position,
)
from sqlmodel import Relationship, SQLModel, Field
from databases.tables.order_table import ExchangeOrderTable, FakeOrderTable
from databases.tables.deal_table import DealTable

# avoids circular imports
# https://sqlmodel.tiangolo.com/tutorial/code-structure/#hero-model-file
if TYPE_CHECKING:
    from bots.models import BotModel


class BotTable(SQLModel, table=True):
    __tablename__ = "bot"

    id: Optional[UUID] = Field(
        default_factory=uuid4, primary_key=True, index=True, nullable=False, unique=True
    )
    pair: str = Field(index=True)
    fiat: str = Field(default="USDC", index=True)
    quote_asset: QuoteAssets = Field(default=QuoteAssets.USDC)
    fiat_order_size: float = Field(
        default=15, ge=0, description="Min Binance 0.0001 BNB approx 15USD"
    )
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailing,
        sa_column=Column(Enum(CloseConditions)),
    )
    cooldown: int = Field(
        default=0,
        description="cooldown period in minutes before opening next bot with same pair",
    )
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
    dynamic_trailing: bool = Field(default=False)
    logs: list = Field(default_factory=list, sa_column=Column(JSON))
    mode: str = Field(default="manual")
    market_type: MarketType = Field(
        default=MarketType.SPOT, sa_column=Column(Enum(MarketType))
    )
    name: str = Field(default="Default bot")
    status: Status = Field(default=Status.inactive, sa_column=Column(Enum(Status)))
    stop_loss: float = Field(
        default=0, description="If stop_loss > 0, allow for reversal"
    )
    margin_short_reversal: bool = Field(default=False)
    take_profit: float = Field(default=0)
    trailing: bool = Field(default=False)
    trailing_deviation: float = Field(
        default=0,
        ge=-1,
        le=101,
        description="Set trailing_deviation once trailing_profit is broken first time",
    )
    trailing_profit: float = Field(
        default=0,
        ge=-1,
        le=101,
        description="Equivalent to take_profit but it moves dynamically based on current price",
    )
    position: Position = Field(default=Position.long, sa_column=Column(Enum(Position)))

    # Table relationships filled up internally
    orders: list[ExchangeOrderTable] = Relationship(
        back_populates="bot",
        sa_relationship_kwargs={
            "lazy": "joined",
            "single_parent": True,
            "order_by": "ExchangeOrderTable.timestamp",
        },
    )
    deal_id: Optional[UUID] = Field(
        default=None, foreign_key="deal.id", ondelete="CASCADE", index=True
    )
    # lazy option will allow objects to be nested when transformed for json return
    deal: DealTable = Relationship(
        sa_relationship_kwargs={"lazy": "joined", "single_parent": True}
    )

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
    }

    @classmethod
    def from_model(cls, model: "BotModel") -> "BotTable":
        """
        Converts a BotModel instance into a BotTable instance for CRUD operations.
        """
        # Use only the fields defined on BotTable
        data = {
            field: getattr(model, field)
            for field in cls.model_fields.keys()
            if hasattr(model, field)
        }
        return cls(**data)

    @field_validator("logs", mode="before")
    def validate_logs(cls, v, info):
        return v

    @field_validator("trailing")
    @classmethod
    def validate_trailing(cls, v, values):
        if v and values.get("trailing_deviation") == 0:
            raise ValueError("Trailing deviation must be set if trailing is enabled")

        if v and values.get("trailing_profit") == 0:
            raise ValueError("Trailing profit must be set if trailing is enabled")

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
    quote_asset: QuoteAssets = Field(default=QuoteAssets.USDC)
    fiat_order_size: float = Field(
        default=15, ge=0, description="Min Binance 0.0001 BNB approx 15USD"
    )
    candlestick_interval: BinanceKlineIntervals = Field(
        default=BinanceKlineIntervals.fifteen_minutes,
        sa_column=Column(Enum(BinanceKlineIntervals)),
    )
    close_condition: CloseConditions = Field(
        default=CloseConditions.dynamic_trailing,
        sa_column=Column(Enum(CloseConditions)),
    )
    cooldown: int = Field(
        default=0,
        description="cooldown period in minutes before opening next bot with same pair",
    )
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
    dynamic_trailing: bool = Field(default=False)
    logs: list = Field(default_factory=list, sa_column=Column(JSON))
    mode: str = Field(default="manual")
    market_type: MarketType = Field(
        default=MarketType.SPOT, sa_column=Column(Enum(MarketType))
    )
    name: str = Field(default="Default bot")
    status: Status = Field(default=Status.inactive, sa_column=Column(Enum(Status)))
    stop_loss: float = Field(
        default=0, description="If stop_loss > 0, allow for reversal"
    )
    margin_short_reversal: bool = Field(default=False)
    take_profit: float = Field(default=0)
    trailing: bool = Field(default=False)
    trailing_deviation: float = Field(
        default=0,
        ge=-1,
        le=101,
        description="Trailing activation (first take profit hit)",
    )
    trailing_profit: float = Field(
        default=0,
        ge=-1,
        le=101,
        description="Equivalent to take_profit but it moves dynamically based on current price",
    )
    position: Position = Field(default=Position.long, sa_column=Column(Enum(Position)))

    # Table relationships filled up internally
    orders: list[FakeOrderTable] = Relationship(
        back_populates="paper_trading",
        sa_relationship_kwargs={"lazy": "joined", "single_parent": True},
    )
    deal_id: Optional[UUID] = Field(
        default=None, foreign_key="deal.id", ondelete="CASCADE", index=True
    )

    # lazy option will allow objects to be nested when transformed for json return
    deal: DealTable = Relationship(
        sa_relationship_kwargs={"lazy": "selectin", "single_parent": True}
    )

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
    }
