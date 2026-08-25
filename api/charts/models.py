import datetime
from pydantic import BaseModel, field_validator
from pybinbot import StandardResponse


class CandlestickItemRequest(BaseModel):
    data: list[list]
    symbol: str
    interval: str  # See EnumDefitions
    limit: int = 600
    offset: int = 0


class CandlestickParams(BaseModel):
    symbol: str
    interval: str  # See EnumDefinitions
    limit: int = 600
    # starTime and endTime must be camel cased for the API
    startTime: float | None = None
    endTime: float | None = None


class MarketDominationSeriesStore(BaseModel):
    timestamp: datetime.datetime
    time: str
    symbol: str
    priceChangePercent: float
    price: float
    volume: float

    @field_validator("priceChangePercent", mode="before")
    @classmethod
    def validate_percentage(cls, v: str | int | float):
        if isinstance(v, str):
            return float(v)
        return v


class MarketDomination(BaseModel):
    time: str
    data: list[MarketDominationSeriesStore]


class MarketDominationResponse(BaseModel):
    data: list[MarketDominationSeriesStore]
    message: str
    error: int = 0


class MarketDominationSeries(BaseModel):
    dates: list[str] = []
    gainers_percent: list[float] = []
    losers_percent: list[float] = []
    gainers_count: list[int] = []
    losers_count: list[int] = []
    total_volume: list[float] = []
    adr_ratio: list[float] = []


class GetMarketDominationResponse(StandardResponse):
    data: MarketDominationSeries


class CandlestickData(BaseModel):
    symbol: str
    interval: str
    open: float
    open_time: int
    close_time: int
    volume: float
    candle_closed: bool
    high: float
    close: float
    low: float
    time: datetime.datetime


class SingleCandle(BaseModel):
    symbol: str
    interval: str
    open: float
    open_time: int
    close_time: int
    volume: float
    high: float
    close: float
    low: float
    time: datetime.datetime


class CandlestickResponse(StandardResponse):
    data: list[CandlestickData]


class TopMoverEntry(BaseModel):
    symbol: str
    price_change_percent: float


class GainersLosersSnapshot(BaseModel):
    source: str
    recorded_at: datetime.datetime
    top_gainers: list[TopMoverEntry]
    top_losers: list[TopMoverEntry]


class GainersLosersSeriesResponse(StandardResponse):
    data: list[GainersLosersSnapshot]


class MarketBreadthSample(BaseModel):
    """
    Ingest payload for one market-breadth sample before it is mapped to the
    database column names.
    """

    timestamp: datetime.datetime
    source: str
    advancers: int
    decliners: int
    market_breadth: float
    avg_gain: float
    avg_loss: float
    total_volume: float
    strength_index: float
