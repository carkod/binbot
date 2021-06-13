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

@research_blueprint.route("/correlation", methods=["GET"])
def get_pearson():
    return Correlation().get_pearson()

@research_blueprint.route("/signals", methods=["GET"])
def get_signals():
    return Correlation().get_signals()
