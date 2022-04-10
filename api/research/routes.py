from flask import Blueprint
from api.research.controller import Controller
from api.research.correlation import Correlation
from threading import Thread, enumerate

research_blueprint = Blueprint("research", __name__)


@research_blueprint.route("/save-correlation/<interval>/<limit>", methods=["GET"])
def save_pearson(interval, limit):
    correlation = Correlation()
    match_thread = next(
        (x for x in enumerate() if x.name == "save_correlation_thread"), None
    )
    if not match_thread:
        thread = Thread(
            name="save_correlation_thread",
            target=correlation.trigger_r,
            args=[interval, limit],
        )
        thread.start()
        return correlation.response()
    else:
        return correlation.block_response()


@research_blueprint.route("/signals", methods=["GET"])
def get_signals():
    return Correlation().get_signals()


@research_blueprint.route("/historical-signals", methods=["GET"])
def get_historical_signals():
    return Correlation().get_historical_signals()


@research_blueprint.route("/blacklist", methods=["POST"])
def post_blacklist():
    return Controller().create_blacklist_item()


@research_blueprint.route("/blacklist/<pair>", methods=["DELETE"])
def delete_blacklist_item(pair):
    return Controller().delete_blacklist_item()


@research_blueprint.route("/blacklist", methods=["PUT"])
def put_blacklist():
    return Controller().edit_blacklist()


@research_blueprint.route("/blacklist", methods=["GET"])
def get_blacklisted():
    return Controller().get_blacklist()


@research_blueprint.route("/controller", methods=["PUT"])
def put_controller():
    return Controller().edit_settings()


@research_blueprint.route("/controller", methods=["GET"])
def get_controller():
    return Controller().get_settings()

@research_blueprint.route("/test-autotrade-settings", methods=["GET"])
def get_test_autotrade_settings():
    return Controller().get_test_autotrade_settings()

@research_blueprint.route("/test-autotrade-settings", methods=["PUT"])
def edit_test_autotrade_settings():
    return Controller().edit_test_autotrade_settings()