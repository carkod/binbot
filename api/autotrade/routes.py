from fastapi import APIRouter
from autotrade.controller import AutotradeSettingsController
from autotrade.schemas import AutotradeSettingsResponse, AutotradeSettingsSchema

autotrade_settings_blueprint = APIRouter()


@autotrade_settings_blueprint.put("/bots", tags=["autotrade settings"])
def edit_settings(item: AutotradeSettingsSchema):
    """
    Autotrade settings for bots
    these use real money and real Binance transactions
    """
    print(item)
    return AutotradeSettingsController().edit_settings(item)


@autotrade_settings_blueprint.get("/bots", response_model=AutotradeSettingsResponse, tags=["autotrade settings"])
def get_settings():
    return AutotradeSettingsController().get_settings()


@autotrade_settings_blueprint.get("/paper-trading", response_model=AutotradeSettingsResponse, tags=["autotrade settings"])
def get_test_autotrade_settings():
    return AutotradeSettingsController(
        document_id="test_autotrade_settings"
    ).get_settings()


@autotrade_settings_blueprint.put("/paper-trading", tags=["autotrade settings"])
def edit_test_autotrade_settings(item: AutotradeSettingsSchema):
    return AutotradeSettingsController(
        document_id="test_autotrade_settings"
    ).edit_settings(item)
