from fastapi import APIRouter
from api.autotrade.controller import AutotradeSettingsController

autotrade_settings_blueprint = APIRouter()


@autotrade_settings_blueprint.put("/bots")
def put_controller():
    """
    Autotrade settings for bots
    these use real money and real Binance transactions
    """
    return AutotradeSettingsController().edit_settings()


@autotrade_settings_blueprint.get("/bots")
def get_controller():
    return AutotradeSettingsController().get_settings()


@autotrade_settings_blueprint.get("/paper-trading")
def get_test_autotrade_settings():
    return AutotradeSettingsController(
        document_id="test_autotrade_settings"
    ).get_settings()


@autotrade_settings_blueprint.put("/paper-trading")
def edit_test_autotrade_settings():
    return AutotradeSettingsController(
        document_id="test_autotrade_settings"
    ).edit_settings()
