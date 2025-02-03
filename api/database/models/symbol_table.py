from sqlmodel import SQLModel, Field
from database.utils import timestamp
from sqlalchemy import BigInteger, Column


class SymbolTable(SQLModel, table=True):
    __tablename__ = "symbol"

    id: str = Field(primary_key=True, description="Symbol")
    created_at: int = Field(
        default_factory=timestamp, sa_column=Column(BigInteger, nullable=False)
    )
    updated_at: int = Field(
        default_factory=timestamp, sa_column=Column(BigInteger, nullable=False)
    )
    active: bool = Field(default=True, description="Blacklisted items = false")
    blacklist_reason: str = Field(default="")
    quote_asset: str = Field(
        default="", description="in BTCUSDC, BTC would be quote asset"
    )
    base_asset: str = Field(
        default="", description="in BTCUSDC, USDC would be base asset"
    )
    price_precision: int = Field(
        default=0,
        description="Usually there are 2 price precisions, one for base and another for quote, here we usually indicate quote, since we always use the same base: USDC",
    )
    qty_precision: int = Field(default=0)
    min_qty: float = Field(default=0, description="Minimum qty (quote asset) value")
    min_notional: float = Field(default=0, description="Minimum price x qty value")
