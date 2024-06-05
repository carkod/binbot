from fastapi import APIRouter

from charts.models import Candlestick, CandlestickItemRequest

charts_blueprint = APIRouter()

@charts_blueprint.get("/timeseries", summary="Retrieve timeseries data", tags=["charts"])
def get_timeseries(symbol: str, limit: int=500):
    """
    Retrieve candlesticks data stored in DB from Binance
    in a timeseries format by Binquant
    """
    return Candlestick().get_timeseries(symbol, limit)
