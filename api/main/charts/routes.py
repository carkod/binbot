from flask import Blueprint
from main.charts.models import Candlestick

charts_blueprint = Blueprint("charts", __name__)


@charts_blueprint.route("/candlestick/<pair>/<interval>", methods=["GET"])
def get(pair, interval):
    return Candlestick().get()
