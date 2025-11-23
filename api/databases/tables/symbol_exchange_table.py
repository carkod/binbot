from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum, Float, ForeignKey
from tools.enum_definitions import ExchangeId
from databases.tables.symbol_table import SymbolTable


class SymbolExchangeTable(SQLModel, table=True):
    __tablename__ = "symbol_exchange"

    id: int = Field(primary_key=True, sa_column_kwargs={"autoincrement": True})
    exchange_id: ExchangeId = Field(
        sa_column=Column(Enum(ExchangeId, name="exchange_id_enum"))
    )
    symbol_id: str = Field(
        sa_column=Column(ForeignKey("symbol.id", ondelete="CASCADE"))
    )
    min_notional: float = Field(
        default=0,
        sa_column=Column(Float),
        description="Minimum price x qty value for this exchange",
    )
    is_margin_trading_allowed: bool = Field(default=False)
    price_precision: int = Field(
        default=0,
        description="Usually there are 2 price precisions, one for base and another for quote, here we usually indicate quote, since we always use the same base: USDC",
    )
    qty_precision: int = Field(default=0)
    symbol: "SymbolTable" = Relationship(back_populates="exchange_values")
