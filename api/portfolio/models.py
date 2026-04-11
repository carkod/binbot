from pybinbot import StandardResponse
from pydantic import BaseModel


class Stats(BaseModel):
    pnl: float
    sharpe: float
    btc_sharpe: float

    class Config:
        extra = "forbid"


class BenchmarkData(BaseModel):
    fiat: list
    btc: list
    dates: list


class BenchmarkSeries(BaseModel):
    series: BenchmarkData
    stats: Stats


class BenchmarkSeriesResponse(StandardResponse):
    data: BenchmarkSeries
