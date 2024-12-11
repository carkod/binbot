from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlmodel import Session
from database.bot_crud import BotTableCrud
from deals.controllers import CreateDealController
from database.models.bot_table import BotTable
from database.utils import get_session
from tools.handle_error import (
    api_response,
    json_response,
    json_response_error,
    json_response_message,
)
from bots.schemas import BotResponse, BotListResponse, ErrorsRequestBody
from typing import List
from tools.exceptions import BinanceErrors, BinbotErrors


bot_blueprint = APIRouter()


@bot_blueprint.get("/bot", response_model=BotListResponse, tags=["bots"])
def get(
    status: str | None = None,
    start_date: float | None = None,
    end_date: float | None = None,
    no_cooldown: bool = True,
    session: Session = Depends(get_session),
):
    try:
        bots = BotTableCrud(session=session).get(
            status, start_date, end_date, no_cooldown
        )
        return api_response(detail="Bots found", data=bots)
    except ValidationError as error:
        return json_response_error(error.json())


@bot_blueprint.get("/bot/active-pairs", tags=["bots"])
def get_active_pairs(
    session: Session = Depends(get_session),
):
    try:
        bot = BotTableCrud(session=session).get_active_pairs()
        return api_response(detail="Active pairs found!", data=bot)
    except ValueError as error:
        return json_response_error(error)


@bot_blueprint.get("/bot/{id}", tags=["bots"])
def get_one_by_id(id: str, session: Session = Depends(get_session)):
    try:
        bot = BotTableCrud(session=session).get_one(bot_id=id, symbol=None)
        if not bot:
            return api_response(detail="Bot not found.", error=1)
        else:
            return api_response(detail="Bot found", data=bot)
    except ValidationError as error:
        return json_response_error(error.json())


@bot_blueprint.get("/bot/{symbol}", tags=["bots"])
def get_one_by_symbol(
    symbol: str,
    session: Session = Depends(get_session),
):
    try:
        bot = BotTableCrud(session=session).get_one(bot_id=None, symbol=symbol)
        return api_response(detail="Bot found", data=bot)
    except ValidationError as error:
        return json_response_error(error.json())


@bot_blueprint.post("/bot", tags=["bots"], response_model=None)
def create(
    bot_item: BotTable,
    session: Session = Depends(get_session),
):
    try:
        bot = BotTableCrud(session=session).create(bot_item)
        return bot
    except ValidationError as error:
        return api_response(message=error.json(), error=1)


@bot_blueprint.put("/bot/{id}", tags=["bots"])
def edit(
    id: str,
    bot_item: BotTable,
    session: Session = Depends(get_session),
):
    try:
        bot = BotTableCrud(session=session).create(bot_item)
        return json_response({"message": "Bot updated", "data": bot})
    except ValidationError as error:
        return json_response_error(error.json())


@bot_blueprint.delete("/bot", tags=["bots"])
def delete(
    id: List[str],
    session: Session = Depends(get_session),
):
    """
    Delete bots, given a list of ids
    """
    try:
        BotTableCrud(session=session).delete(id)
        return json_response_message("Bots deleted successfully.")
    except ValidationError as error:
        return json_response_error(error.json())


@bot_blueprint.get("/bot/activate/{id}", tags=["bots"])
async def activate_by_id(id: str, session: Session = Depends(get_session)):
    """
    Activate bot

    - Creates deal
    - If changes were made, it will override DB data
    - Because botId is received from endpoint, it will be a str not a PyObjectId
    """
    bot = BotTableCrud(session=session).get_one(bot_id=id)
    if not bot:
        return json_response_error("Bot not found.")

    bot_instance = CreateDealController(bot, db_table=BotTable)

    try:
        bot_instance.open_deal()
        return json_response_message("Successfully activated bot!")
    except BinbotErrors as error:
        bot_instance.controller.update_logs(bot_id=id, log_message=error.message)
        return json_response_error(error.message)
    except BinanceErrors as error:
        bot_instance.controller.update_logs(bot_id=id, log_message=error.message)
        return json_response_error(error.message)


@bot_blueprint.delete("/bot/deactivate/{id}", tags=["bots"])
def deactivation(id: str, session: Session = Depends(get_session)):
    """
    Deactivation means closing all deals and selling to
    fiat. This is often used to prevent losses
    """
    bot_model = BotTableCrud(session=session).get_one(bot_id=id)
    if not bot_model:
        return json_response_message("No active bot found.")

    bot_instance = CreateDealController(bot_model, db_table=BotTable)
    try:
        bot_instance.close_all()
        return json_response_message(
            "Active orders closed, sold base asset, deactivated"
        )
    except BinbotErrors as error:
        bot_instance.controller.update_logs(bot_id=id, log_message=error.message)
        return json_response_error(error.message)


@bot_blueprint.post("/bot/errors/{bot_id}", tags=["bots"])
def bot_errors(
    bot_id: str, bot_errors: ErrorsRequestBody, session: Session = Depends(get_session)
):
    """
    POST errors to a bot

    - If error(s) is received from endpoint, get it from request body
    - Else use `post_errors_by_id` method for internal calls
    """
    request_body = bot_errors.model_dump(mode="python")
    bot_errors = request_body.get("errors", None)
    try:
        BotTableCrud(session=session).update_logs(bot_errors, bot_id=bot_id)
    except Exception as error:
        return json_response_error(f"Error posting errors: {error}")
    return json_response_message("Errors posted successfully.")
