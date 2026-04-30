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


class AdrSeriesDb(BaseModel):
    """
    Ingest payload for one market_breadth row. Mirrors the SQL columns 1:1
    so model_dump() can be passed straight into MarketBreadthTable(**dump).
    """

    timestamp: datetime.datetime
    source: str
    advancers: int
    decliners: int
    adp: float
    avg_gain: float
    avg_loss: float
    total_volume: float
    strength_index: float


class AdrSeries(BaseModel):
    """
    Read shape returned by GET /charts/adr-series.

    Parallel arrays (newest-first) so the frontend can plot directly without
    pivoting. Every field except adp_ma is read straight from the stored
    columns; adp_ma is a rolling window computed in SQL.
    """

    timestamp: list[str]
    advancers: list[int]
    decliners: list[int]
    adp: list[float]
    adp_ma: list[float | None]
    avg_gain: list[float]
    avg_loss: list[float]
    total_volume: list[float]
    strength_index: list[float]


class AdrSeriesResponse(StandardResponse):
    data: AdrSeries
