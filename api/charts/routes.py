from flask import Blueprint
from api.charts.models import Candlestick

charts_blueprint = Blueprint("charts", __name__)

@charts_blueprint.route("/candlestick/<pair>/<interval>", methods=["GET"])
def get(pair, interval):
    return Candlestick(interval).get()

@charts_blueprint.route("/change/<pair>/<interval>", methods=["GET"])
def get_diff(pair, interval):
    return Candlestick().get_diff()
