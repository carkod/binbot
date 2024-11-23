from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from tools.handle_error import json_response, json_response_error
from autotrade.controller import AutotradeSettingsController
from autotrade.schemas import AutotradeSettingsResponse, AutotradeSettingsSchema

autotrade_settings_blueprint = APIRouter()


@autotrade_settings_blueprint.put("/bots", tags=["autotrade settings"])
def edit_settings(item: AutotradeSettingsSchema):
    """
    Autotrade settings for bots
    these use real money and real Binance transactions
    """
    try:
        AutotradeSettingsController().edit_settings(item)
        return json_response({"message": "Successfully updated settings"})
    except ValidationError as error:
        msg = ""
        for field, desc in error.args[0].items():
            msg += field + desc[0]
        resp = json_response_error(f"{msg}")
        return resp


@autotrade_settings_blueprint.get(
    "/bots", response_model=AutotradeSettingsResponse, tags=["autotrade settings"]
)
def get_settings():
    try:
        deserialized_data = AutotradeSettingsController().get_settings()
        return json_response(
            {
                "message": "Successfully retrieved settings",
                "data": deserialized_data.model_dump(),
            }
        )
    except Exception as error:
        return json_response_error(f"Error getting settings: {error}")


@autotrade_settings_blueprint.get(
    "/paper-trading",
    response_model=AutotradeSettingsResponse,
    tags=["autotrade settings"],
)
def get_test_autotrade_settings():
    try:
        deserialized_data = AutotradeSettingsController(
            document_id="test_autotrade_settings"
        ).get_settings()
        return json_response(
            {
                "message": "Successfully retrieved settings",
                "data": deserialized_data.model_dump(),
            }
        )
    except Exception as error:
        return json_response_error(f"Error getting settings: {error}")


@autotrade_settings_blueprint.put("/paper-trading", tags=["autotrade settings"])
def edit_test_autotrade_settings(item: AutotradeSettingsSchema):
    try:
        data = AutotradeSettingsController(
            document_id="test_autotrade_settings"
        ).edit_settings(item)
        if not data:
            raise HTTPException(status_code=404, detail="Autotrade settings not found")
        else:
            return json_response(
                {"message": "Successfully updated settings", "data": data}
            )
    except ValidationError as error:
        msg = ""
        for field, desc in error.args[0].items():
            msg += field + desc[0]
        resp = json_response_error(f"{msg}")
        return resp
