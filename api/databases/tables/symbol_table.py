from sqlmodel import SQLModel, Field, Relationship
from databases.utils import timestamp
from sqlalchemy import BigInteger, Column
from pydantic import field_validator
from databases.tables.asset_index_table import SymbolIndexLink
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from databases.tables.asset_index_table import AssetIndexTable
    from databases.tables.symbol_exchange_table import SymbolExchangeTable


class SymbolTable(SQLModel, table=True):
    __tablename__ = "symbol"

    id: str = Field(primary_key=True, description="Symbol")
    created_at: int = Field(
        default_factory=timestamp, sa_column=Column(BigInteger, nullable=False)
    )
    updated_at: int = Field(
        default=timestamp(), sa_column=Column(BigInteger, nullable=False)
    )
    active: bool = Field(default=True, description="Blacklisted items = False")
    blacklist_reason: str = Field(default="")
    description: str = Field(default="", description="Description of the symbol")
    quote_asset: str = Field(
        default="", description="in DOGEUSDC, DOGE would be quote asset"
    )
    base_asset: str = Field(
        default="", description="in DOGEUSDC, USDC would be base asset"
    )
    cooldown: int = Field(default=0, description="Time in seconds between trades")
    cooldown_start_ts: int = Field(
        default=0,
        description="Timestamp when cooldown started in milliseconds",
        sa_type=BigInteger,
    )
    exchange_values: list["SymbolExchangeTable"] = Relationship(
        back_populates="symbol",
        sa_relationship_kwargs={
            "lazy": "joined",
            "single_parent": True,
        },
    )
    asset_indices: list["AssetIndexTable"] = Relationship(
        back_populates="symbols",
        link_model=SymbolIndexLink,
        sa_relationship_kwargs={
            "lazy": "joined",
            "single_parent": True,
        },
    )

    class Config:
        from_attributes = True

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
