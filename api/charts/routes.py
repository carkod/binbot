from crypt import methods
from flask import Blueprint
from api.charts.models import Candlestick

charts_blueprint = Blueprint("charts", __name__)


@charts_blueprint.route("/klines")
def get_klines():
    """
    Query params
    pair=string
    interval (optional)
    limit=int (optional)
    offset=int (optional)
    """
    return Candlestick().get_klines()

@charts_blueprint.route("/klines", methods=["PUT"])
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

@charts_blueprint.route("/klines", methods=["DELETE"])
def delete_klines():
    """
    Query params
    symbol
    """
    return Candlestick().delete_klines()

@charts_blueprint.route("/candlestick/<pair>/<interval>", defaults={"stats": None})
@charts_blueprint.route("/candlestick/<pair>/<interval>/<stats>", methods=["GET"])
def get(pair, interval, stats):
    return Candlestick().get()


@charts_blueprint.route("/change/<pair>/<interval>", methods=["GET"])
def get_diff(pair, interval):
    return Candlestick().get_diff()
