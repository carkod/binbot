from sqlmodel import SQLModel, Field
from database.utils import timestamp
from sqlalchemy import BigInteger, Column
from pydantic import field_validator


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
    cooldown: int = Field(default=0, description="Time in seconds between trades")
    cooldown_start_ts: int = Field(
        default=0,
        description="Timestamp when cooldown started in milliseconds",
        sa_type=BigInteger,
    )

    @field_validator("cooldown", "cooldown_start_ts")
    @classmethod
    def validate_cooldown(cls, value: int):
        """
        Both fields are required if one of them is filled in
        """
        if value > 0 and cls.cooldown_start_ts == 0:
            raise ValueError("cooldown_start_ts is required when cooldown is filled")

        if value > 0 and cls.cooldown == 0:
            raise ValueError("cooldown is required when cooldown timestamp is filled")

        return value
