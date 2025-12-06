from pydantic import BaseModel, Field
from tools.handle_error import StandardResponse
from typing import Dict


class BalanceSchema(BaseModel):
    """
    Blueprint of the bots collection on MongoDB
    All validation and database fields new or old handled here
    """

    balances: Dict[str, float] = Field(
        default={}, description="Dictionary of asset balances 'BTC': 0.5, 'ETH': 0.01"
    )
    estimated_total_fiat: float = Field(
        default=0,
        description="Estimated total in fiat currency e.g. USD or tether token",
    )
    fiat_available: float = Field(
        default=0, description="Amount of fiat currency left unallocated"
    )
    fiat_currency: str = Field(
        default="USDT",
        description="Fiat currency use for trading, this should match autotrade.settings.fiat",
    )


class BalanceResponse(StandardResponse):
    data: BalanceSchema


class ListSymbolsResponse(StandardResponse):
    data: list[str]


class BinanceBalanceResponse(BaseModel):
    asset: str
    free: float
    locked: float


class Binance24Ticker(BaseModel):
    symbol: str
    priceChange: str
    priceChangePercent: str
    weightedAvgPrice: str
    prevClosePrice: str
    lastPrice: str
    lastQty: str
    bidPrice: str
    bidQty: str
    askPrice: str
    askQty: str
    openPrice: str
    highPrice: str
    lowPrice: str
    volume: str
    quoteVolume: str
    openTime: int
    closeTime: int
    firstId: int
    lastId: int
    count: int


class BinanceBalance(BaseModel):
    asset: str
    free: float
    locked: float


class GainersLosersResponse(StandardResponse):
    data: list[Binance24Ticker]


class EstimatedBalance(BaseModel):
    time: str
    assets: list
    estimated_total_usdc: float


class EstimatedBalancesResponse(StandardResponse):
    data: EstimatedBalance


class BalanceSeries(BaseModel):
    usdc: list
    btc: list
    dates: list


class BalanceSeriesResponse(StandardResponse):
    data: BalanceSeries
