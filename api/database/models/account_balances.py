from typing import Optional
from pydantic import field_validator
from sqlalchemy import JSON, Column
from database.utils import timestamp
from sqlmodel import SQLModel, Field


class ExchangeInfoTable(SQLModel, table=True):
    """
    Temporary design of new consolidated table for all balance data this includes:

    - Old MongoDB balance data
    - New plans to include exchange info data
    - Old blacklist data then would become redundant
    - Single source of truth for all exchanges, so an field indicating exchange must be included
    """

    __tablename__ = "exchange_info"

    symbol: str = Field(index=True, primary_key=True, nullable=False, unique=True)
    base_asset: str = Field(
        index=True, description="Base asset of the symbol e.g. BTCUSDC -> BTC"
    )
    binance_exchange_info: dict = Field(sa_column=Column(JSON), description="For now, this is the full binance exchange info to make things easier")
    created_at: float = Field(default_factory=timestamp)
    updated_at: float = Field(default_factory=timestamp)

    model_config = {
        "from_attributes": True,
        "use_enum_values": True,
    }

    @field_validator("logs", mode="before")
    def validate_logs(cls, v, info):
        return v


class ConsolidatedBalancesTable(SQLModel, table=True):
    """
    Replacement of old MongoDB balances collection
    future plans include consolidation with all connected exchanges

    - id is a unique timestamp to support series. This should be ingested as before, once per day

    """

    __tablename__ = "consolidated_balances"

    id: float = Field(default_factory=timestamp, primary_key=True, unique=True, index=True, nullable=False)
    asset: str = Field(index=True, nullable=False)
    free: Optional[float] = Field(default=0)
    estimated_total_fiat: Optional[float] = Field(default=0, description="This is derived from free * price of fiat, which is determined in autotrade")
