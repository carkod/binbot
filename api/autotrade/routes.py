from flask import Blueprint

from api.autotrade.controller import AutotradeSettingsController

autotrade_settings_blueprint = Blueprint("autotrade_settings", __name__)


@autotrade_settings_blueprint.route("/bots", methods=["PUT"])
def put_controller():
    """
    Autotrade settings for bots
    these use real money and real Binance transactions
    """
    return AutotradeSettingsController().edit_settings()


@autotrade_settings_blueprint.route("/bots", methods=["GET"])
def get_controller():
    return AutotradeSettingsController().get_settings()


@autotrade_settings_blueprint.route("/paper-trading", methods=["GET"])
def get_test_autotrade_settings():
    return AutotradeSettingsController(
        document_id="test_autotrade_settings"
    ).get_settings()


@autotrade_settings_blueprint.route("/paper-trading", methods=["PUT"])
def edit_test_autotrade_settings():
    return AutotradeSettingsController(
        document_id="test_autotrade_settings"
    ).edit_settings()
