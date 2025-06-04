import datetime
from pydantic import BaseModel, field_validator
from tools.handle_error import StandardResponse
from bson.objectid import ObjectId


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


class KlineProduceModel(BaseModel):
    symbol: str
    open_time: str
    close_time: str
    open_price: str
    close_price: str
    high_price: str
    low_price: str
    volume: float


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
    open_time: datetime.datetime
    volume: float
    candle_closed: bool
    high: float
    close: float
    low: float
    end_time: int
    _id: ObjectId


class CandlestickResponse(StandardResponse):
    data: list[CandlestickData]


class AdrSeriesDb(BaseModel):
    """
    Replacement for MarketDominationSeriesStore
    which should in theory take less space in the database
    and still provide the necessary data for market domination analysis.
    """

    timestamp: datetime.datetime
    advancers: int
    decliners: int
    total_volume: float


class AdrSeries(StandardResponse):
    adr: float
    advancers: int
    decliners: int
    total_volume: float
    timestamp: str

    @field_validator("timestamp", mode="after")
    @classmethod
    def format_timestamp(cls, v: datetime.datetime):
        if isinstance(v, datetime.datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")

    @field_validator("timestamp", mode="after")
    @classmethod
    def convert_id(cls, v: str):
        if isinstance(v, ObjectId):
            return str(v)
        return v


class AdrSeriesResponse(StandardResponse):
    data: list[AdrSeries]
