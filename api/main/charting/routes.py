from flask import Blueprint
from main.charting.models import Candlestick

klines_blueprint = Blueprint("klines", __name__)


@klines_blueprint.route("/<pair>/<interval>", methods=["GET"])
def get(pair, interval):
    return Candlestick().get()
