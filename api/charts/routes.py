from fastapi import APIRouter

from api.charts.models import Candlestick, CandlestickItem

charts_blueprint = APIRouter()


@charts_blueprint.put("/candlestick", summary="Update klines stored in the DB")
def update_klines(item: CandlestickItem):
    """
    json
    {
        "data": [[array]],
        "symbol": string,
        "interval: enum[string]
        "limit": int (optional) default: 300
        "offset": int (optional) default: 0
    }
    """
    return Candlestick().update_klines(item)


@charts_blueprint.delete("/candlestick", summary="Delete Klines stored in the DB")
def delete_klines(symbol: CandlestickItem):
    """
    Query params

    symbol
    """
    return Candlestick().delete_klines()


@charts_blueprint.get("/candlestick", summary="Retrieved klines stored in DB")
def get():
    """
    @json:
        {
            "pair": string,
            "interval": string,
            "stats": boolean, Additional statistics such as MA, amplitude, volume, candle spreads
            "binance": boolean, whether to directly pull data from binance or from DB
            "limit": int,
            "start_time": int
            "end_time": int
        }
    """
    return Candlestick().get()
