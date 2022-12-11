from flask import Blueprint

from api.charts.models import Candlestick

charts_blueprint = Blueprint("charts", __name__)


@charts_blueprint.route("/candlestick", methods=["PUT"])
def update_klines():
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
    return Candlestick().update_klines()


@charts_blueprint.route("/candlestick", methods=["DELETE"])
def delete_klines():
    """
    Query params

    symbol
    """
    return Candlestick().delete_klines()


@charts_blueprint.route("/candlestick")
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
