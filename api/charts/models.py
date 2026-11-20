import datetime
from pydantic import BaseModel
from pybinbot import StandardResponse


class TopMoverEntry(BaseModel):
    symbol: str
    price_change_percent: float
    last_price: float | None = None
    turnover_24h: float | None = None


class GainersLosersSnapshot(BaseModel):
    source: str
    recorded_at: datetime.datetime
    top_gainers: list[TopMoverEntry]
    top_losers: list[TopMoverEntry]


class GainersLosersSeriesResponse(StandardResponse):
    data: list[GainersLosersSnapshot]


class GainersLosersAggregatePoint(BaseModel):
    timestamp: datetime.datetime
    gainer_magnitude: float
    loser_magnitude: float
    advancers: int
    decliners: int


class GainersLosersAggregateResponse(StandardResponse):
    data: list[GainersLosersAggregatePoint]


class FastestMoverEntry(BaseModel):
    symbol: str
    price_change_1h_percent: float
    price_change_3h_percent: float | None = None
    price_change_percent: float
    last_price: float
    turnover_24h: float


class FastestMoversSnapshot(BaseModel):
    source: str
    recorded_at: datetime.datetime | None
    comparison_at: datetime.datetime | None
    gainers: list[FastestMoverEntry]
    losers: list[FastestMoverEntry]


class FastestMoversResponse(StandardResponse):
    data: FastestMoversSnapshot


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


class CvdAggregatePoint(BaseModel):
    timestamp: datetime.datetime
    buy: float | None
    sell: float | None
    cvd: float | None
    expected_symbols: int | None
    covered_symbols: int
    observed_minutes: int
    complete: bool
    gap: bool
    current: bool
    universe_changed: bool


class CvdAggregateResponse(BaseModel):
    source: str
    data: list[CvdAggregatePoint]
    reset_at: datetime.datetime
    updated_at: datetime.datetime | None
    stale: bool
    partial: bool


class CvdSymbolResponse(CvdAggregateResponse):
    symbol: str
