from flask import Blueprint
from api.research.correlation import Correlation
from threading import Thread
from api.research.blacklisted import Blacklisted

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


@research_blueprint.route("/blacklisted", methods=["GET"])
def get_blacklisted():
    return Blacklisted().get_blacklisted()

@research_blueprint.route("/blacklisted", methods=["POST"])
def save_blacklisted():
    return Blacklisted().save_blacklisted()
