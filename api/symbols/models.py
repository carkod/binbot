from typing import Optional, Sequence
from pybinbot import ExchangeId, StandardResponse, AssetIndexModel, SymbolModel
from databases.tables.symbol_table import SymbolTable
from pydantic import Field, BaseModel


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
                symbol["is_margin_trading_allowed"] = s.exchange_values[
                    0
                ].is_margin_trading_allowed
                symbol["price_precision"] = s.exchange_values[0].price_precision
                symbol["qty_precision"] = s.exchange_values[0].qty_precision
                symbol["min_notional"] = s.exchange_values[0].min_notional

            new_data.append(symbol)

        return new_data


class SymbolRequestPayload(BaseModel):
    symbol: str
    blacklist_reason: str = ""
    active: bool = True
    cooldown: Optional[int] = 0
    cooldown_start_ts: Optional[int] = Field(
        default=0,
        description="Timestamp to indicate when cooldown should start in milliseconds. Combined with cooldown this will put the symbol in inactive for that period of time.",
    )
    futures_leverage: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Default leverage to use for this symbol when trading futures",
    )
    exchange_id: ExchangeId = Field(
        description="Exchange name where this symbol belongs to",
    )
    min_notional: float = 0
    is_margin_trading_allowed: bool = False
    price_precision: int = 0
    qty_precision: int = 0
    quote_asset: str = Field(default="")
    base_asset: str = Field(default="")
    asset_indices: list[AssetIndexModel] = Field(
        default=[], description="List of asset index IDs"
    )


class GetOneSymbolResponse(StandardResponse):
    data: Optional[SymbolModel] = Field(default=None)
