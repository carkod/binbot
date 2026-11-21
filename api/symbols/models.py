from pybinbot import ExchangeId, StandardResponse, SymbolModel
from pydantic import BaseModel, Field


class SymbolRequestPayload(BaseModel):
    symbol: str
    blacklist_reason: str = ""
    active: bool = True
    cooldown: int | None = 0
    cooldown_start_ts: int | None = Field(
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
    multiplier: float = Field(
        default=1.0,
        description="Futures contract multiplier: quantity of the underlying "
        "asset represented by one contract. Not meaningful for spot/margin.",
    )
    quote_asset: str = Field(default="")
    base_asset: str = Field(default="")


class GetOneSymbolResponse(StandardResponse):
    data: SymbolModel | None = Field(default=None)
