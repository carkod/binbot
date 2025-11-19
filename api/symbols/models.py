from typing import Optional, Sequence
from tools.enum_definitions import ExchangeId
from tools.handle_error import StandardResponse
from databases.tables.symbol_table import SymbolTable
from pydantic import Field, BaseModel
from time import time


class AssetIndexModel(BaseModel):
    id: str = Field(description="Unique ID")
    name: str = Field(default="", description="Name of the index")


class SymbolModel(BaseModel):
    """
    Pydantic model for SymbolTable.
    This model has to be kept identical with databases.tables.SymbolTable

    It's harder to manage SymbolTable,
    closing session will remove the nested children objects
    missing Pydantic methods
    """

    id: str = Field(description="Symbol/Pair")
    created_at: int = Field(default_factory=lambda: int(time() * 1000))
    updated_at: int = Field(default_factory=lambda: int(time() * 1000))
    active: bool = Field(default=True, description="Blacklisted items = False")
    blacklist_reason: str = Field(default="")
    description: str = Field(default="", description="Description of the symbol")
    is_margin_trading_allowed: bool = Field(default=False)
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
    min_notional: float = Field(default=0, description="Minimum price x qty value")
    cooldown: int = Field(default=0, description="Time in seconds between trades")
    cooldown_start_ts: int = Field(
        default=0,
        description="Timestamp when cooldown started in milliseconds",
    )
    exchange_id: ExchangeId = Field(
        description="Exchange name where this symbol belongs to",
    )
    asset_indices: list[AssetIndexModel] = Field(
        default=[], description="list of asset indices e.g. memecoin"
    )


class SymbolsResponse(StandardResponse):
    data: Sequence[SymbolTable] = Field(default=[])

    model_config = {"from_attributes": True}

    @classmethod
    def dump_from_table(cls, symbols: Sequence[SymbolTable]):
        """
        Same as model_dump() but from
        BotTable

        Use model_validate to cast/pre-validate data to avoid unecessary validation errors
        """
        new_data = []
        for s in symbols:
            symbol = s.model_dump()
            symbol["asset_indices"] = []
            if len(s.asset_indices) > 0:
                for asset in s.asset_indices:
                    symbol["asset_indices"].append(asset.model_dump())

            if len(s.exchange_values) > 0:
                exchange = s.exchange_values[0]
                symbol.update(exchange.model_dump())

            new_data.append(symbol)

        return new_data


class SymbolPayload(BaseModel):
    id: str
    blacklist_reason: str = ""
    active: bool = True
    cooldown: int = 0
    cooldown_start_ts: int = Field(
        default=0,
        description="Timestamp to indicate when cooldown should start in milliseconds. Combined with cooldown this will put the symbol in inactive for that period of time.",
    )
    exchange_id: ExchangeId = Field(
        description="Exchange name where this symbol belongs to",
    )
    symbol_id: str = Field(description="Symbol/Pair")
    min_notional: float = 0
    is_margin_trading_allowed: bool = False
    price_precision: int = 0
    qty_precision: int = 0
    asset_indices: list[AssetIndexModel] = Field(
        default=[], description="List of asset index IDs"
    )


class GetOneSymbolResponse(StandardResponse):
    data: Optional[SymbolModel] = Field(default=None)
