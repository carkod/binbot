from flask import Blueprint
from api.research.correlation import Correlation
from threading import Thread

research_blueprint = Blueprint("research", __name__)

@research_blueprint.route("/save-correlation/<interval>/<limit>", methods=["GET"])
def save_pearson(interval, limit):
    correlation = Correlation()
    thread = Thread(target=correlation.trigger_r, args=[interval, limit])
    thread.start()
    return correlation.response()

@research_blueprint.route("/signals", methods=["GET"])
def get_signals():
    return Correlation().get_signals()


@research_blueprint.route("/historical-signals", methods=["GET"])
def get_historical_signals():
    return Correlation().get_historical_signals()
