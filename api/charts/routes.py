from fastapi import APIRouter

from charts.models import Candlestick, CandlestickItemRequest

charts_blueprint = APIRouter()


@charts_blueprint.put(
    "/candlestick", summary="Update klines stored in the DB", tags=["charts"]
)
def update_klines(item: CandlestickItemRequest):
    """
    Update candlestick graph data in DB
    """
    return Candlestick().update_klines(item)


@charts_blueprint.delete(
    "/candlestick", summary="Delete Klines stored in the DB", tags=["charts"]
)
def delete_klines(symbol):
    """
    Delete candlestick graph data in DB by symbol.

    This is used to update candlestick data that contains gaps and inconsistencies
    """
    return Candlestick().delete_klines(symbol)


@charts_blueprint.get(
    "/candlestick", summary="Retrieved klines stored in DB", tags=["charts"]
)
def get(symbol: str, interval: str="15m", limit: int=500, start_time: float | None=None, end_time: float | None=None):
    """
    Retrieve existing candlestick data stored in DB from Binance
    """
    return Candlestick().get(symbol, interval, limit, start_time, end_time)
