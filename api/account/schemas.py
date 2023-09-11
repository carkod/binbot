from datetime import datetime

from pydantic import BaseModel
from tools.handle_error import StandardResponse


class BalanceSchema(BaseModel):
    """
    Blueprint of the bots collection on MongoDB
    All validation and database fields new or old handled here
    """

    time: str = datetime.utcnow().strftime("%Y-%m-%d")
    balances: list = []
    estimated_total_usdt: float = 0


class BalanceResponse(StandardResponse):
    data: list[BalanceSchema]


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
    estimated_total_usdt: float


class EstimatedBalancesResponse(StandardResponse):
    data: EstimatedBalance


class BalanceSeries(StandardResponse):
    usdt: list[float]
    btc: list[float]
    dates: list[str]


class BalanceSeriesResponse(StandardResponse):
    data: list[BalanceSeries]
