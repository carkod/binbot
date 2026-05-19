from uuid import UUID, uuid4

from pybinbot import ExchangeId, GridLadderStatus, MarketType, timestamp
from sqlalchemy import JSON, Column, Enum, Index, text
from sqlmodel import Field, Relationship, SQLModel

_ACTIVE_GRID_LADDER_WHERE = text(
    "status IN ('"
    + "', '".join(
        (
            GridLadderStatus.pending.value,
            GridLadderStatus.active.value,
            GridLadderStatus.closing.value,
        )
    )
    + "')"
)


class GridLadderTable(SQLModel, table=True):
    __tablename__ = "grid_ladder"
    __table_args__ = (
        Index(
            "ix_grid_ladder_active_symbol",
            "symbol",
            unique=True,
            postgresql_where=_ACTIVE_GRID_LADDER_WHERE,
            sqlite_where=_ACTIVE_GRID_LADDER_WHERE,
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, unique=True)
    symbol: str = Field(index=True)
    fiat: str = Field(default="USDC", index=True)
    exchange: ExchangeId = Field(
        default=ExchangeId.KUCOIN,
        sa_column=Column(Enum(ExchangeId, name="grid_ladder_exchange_enum")),
    )
    market_type: MarketType = Field(
        default=MarketType.FUTURES,
        sa_column=Column(Enum(MarketType, name="grid_ladder_market_type_enum")),
    )
    algorithm_name: str = Field(default="fixed_grid", index=True)
    status: GridLadderStatus = Field(
        default=GridLadderStatus.pending,
        sa_column=Column(
            Enum(GridLadderStatus, name="grid_ladder_status_enum"),
            nullable=False,
            index=True,
        ),
    )
    range_low: float = Field(gt=0)
    range_high: float = Field(gt=0)
    grid_step: float = Field(gt=0)
    level_count: int = Field(ge=3)
    total_margin: float = Field(gt=0)
    reserved_margin: float = Field(default=0, ge=0)
    used_margin: float = Field(default=0, ge=0)
    realized_pnl: float = Field(default=0)
    unrealized_pnl: float = Field(default=0)
    breakout_low: float = Field(gt=0)
    breakout_high: float = Field(gt=0)
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
    closed_at: float | None = Field(default=None)
    context: dict = Field(default_factory=dict, sa_column=Column(JSON))

    levels: list["GridLevelTable"] = Relationship(
        back_populates="ladder",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "order_by": "GridLevelTable.level_index",
        },
    )
    orders: list["GridOrderTable"] = Relationship(
        back_populates="ladder",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    model_config = {"from_attributes": True, "use_enum_values": True}


class GridLevelTable(SQLModel, table=True):
    __tablename__ = "grid_level"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, unique=True)
    ladder_id: UUID = Field(
        foreign_key="grid_ladder.id", ondelete="CASCADE", index=True
    )
    level_index: int = Field(ge=0, index=True)
    price: float = Field(gt=0)
    side: str = Field(default="neutral", index=True)
    contracts: int = Field(default=0, ge=0)
    margin_required: float = Field(default=0, ge=0)
    status: str = Field(default="pending", index=True)
    entry_order_id: str | None = Field(default=None, index=True)
    take_profit_order_id: str | None = Field(default=None, index=True)
    filled_entry_price: float | None = Field(default=None)
    filled_entry_qty: float = Field(default=0, ge=0)
    take_profit_price: float | None = Field(default=None)
    realized_pnl: float = Field(default=0)
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)

    ladder: GridLadderTable = Relationship(back_populates="levels")
    orders: list["GridOrderTable"] = Relationship(
        back_populates="level",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    model_config = {"from_attributes": True}


class GridOrderTable(SQLModel, table=True):
    __tablename__ = "grid_order"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True, unique=True)
    ladder_id: UUID = Field(
        foreign_key="grid_ladder.id", ondelete="CASCADE", index=True
    )
    level_id: UUID | None = Field(
        default=None, foreign_key="grid_level.id", ondelete="SET NULL", index=True
    )
    exchange_order_id: str = Field(index=True)
    client_oid: str = Field(default="", index=True)
    order_role: str = Field(index=True)
    side: str = Field(index=True)
    price: float = Field(gt=0)
    contracts: int = Field(ge=0)
    status: str = Field(default="open", index=True)
    filled_qty: float = Field(default=0, ge=0)
    filled_price: float | None = Field(default=None)
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)
    raw_response: dict = Field(default_factory=dict, sa_column=Column(JSON))

    ladder: GridLadderTable = Relationship(back_populates="orders")
    level: GridLevelTable | None = Relationship(back_populates="orders")

    model_config = {"from_attributes": True}
