from typing import Annotated

from sqlmodel import Session
from databases.crud.autotrade_crud import AutotradeCrud
from tools.enum_definitions import AutotradeSettingsDocument
from databases.utils import get_session
from autotrade.schemas import (
    AutotradeSettingsSchema,
    TestAutotradeSettingsSchema,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from tools.handle_error import json_response, json_response_error
from user.services.auth import decode_access_token

autotrade_settings_blueprint = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@autotrade_settings_blueprint.put(
    "/bots",
    dependencies=[Depends(decode_access_token)],
    tags=["autotrade settings"],
)
def edit_settings(
    item: AutotradeSettingsSchema, session: Session = Depends(get_session)
):
    """
    Autotrade settings for bots
    these use real money and real Binance transactions
    """
    try:
        result = AutotradeCrud(session=session).edit_settings(item)
        if not result:
            raise HTTPException(status_code=404, detail="Autotrade settings not found")
        return json_response({"message": "Successfully updated settings"})
    except ValidationError as error:
        msg = ""
        for field, desc in error.args[0].items():
            msg += field + desc[0]
        resp = json_response_error(f"{msg}")
        return resp


@autotrade_settings_blueprint.get(
    "/bots",
    dependencies=[Depends(decode_access_token)],
    tags=["autotrade settings"],
)
def get_settings(session: Session = Depends(get_session)):
    try:
        deserialized_data = AutotradeCrud(session=session).get_settings()
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
    dependencies=[Depends(decode_access_token)],
    response_model=TestAutotradeSettingsSchema,
    tags=["autotrade settings"],
)
def get_test_autotrade_settings(
    session: Session = Depends(get_session),
):
    try:
        deserialized_data = AutotradeCrud(
            document_id=AutotradeSettingsDocument.test_autotrade_settings,
            session=session,
        ).get_settings()
        return json_response(
            {
                "message": "Successfully retrieved settings",
                "data": deserialized_data.model_dump(),
            }
        )
    except Exception as error:
        return json_response_error(f"Error getting settings: {error}")


@autotrade_settings_blueprint.put(
    "/paper-trading",
    dependencies=[Depends(decode_access_token)],
    tags=["autotrade settings"],
)
def edit_test_autotrade_settings(
    item: TestAutotradeSettingsSchema,
    session: Session = Depends(get_session),
):
    try:
        data = AutotradeCrud(
            document_id=AutotradeSettingsDocument.test_autotrade_settings,
            session=session,
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
