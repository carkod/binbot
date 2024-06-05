import logging
from fastapi import APIRouter, Query
from deals.controllers import CreateDealController
from tools.handle_error import json_response, json_response_error, json_response_message
from bots.controllers import Bot
from bots.schemas import BotSchema, BotListResponse, ErrorsRequestBody
from typing import List
from tools.exceptions import BinanceErrors, BinbotErrors

bot_blueprint = APIRouter()


@bot_blueprint.get("/bot", response_model=BotListResponse, tags=["bots"])
def get(
    status: str | None = None,
    start_date: float | None = None,
    end_date: float | None = None,
    no_cooldown: bool = True,
):
    return Bot(collection_name="bots").get(status, start_date, end_date, no_cooldown)


@bot_blueprint.get("/bot/{id}", tags=["bots"])
def get_one_by_id(id: str):
    try:
        bot = Bot(collection_name="bots").get_one(bot_id=id, symbol=None)
        if not bot:
            return json_response_error("Bot not found.")
        else:
            return json_response({"message": "Bot found", "data": bot})
    except ValueError as error:
        return json_response_error(error)

@bot_blueprint.get("/bot/{symbol}", tags=["bots"])
def get_one_by_symbol(symbol: str):
    try:
        bot = Bot(collection_name="bots").get_one(bot_id=None, symbol=symbol)
        return json_response({"message": "Bot found", "data": bot})
    except ValueError as error:
        return json_response_error(error)

@bot_blueprint.post("/bot", tags=["bots"])
def create(bot_item: BotSchema):
    return Bot(collection_name="bots").create(bot_item)


@bot_blueprint.put("/bot/{id}", tags=["bots"])
def edit(id: str, bot_item: BotSchema):
    return Bot(collection_name="bots").edit(id, bot_item)


@bot_blueprint.delete("/bot", tags=["bots"])
def delete(id: List[str] = Query(...)):
    """
    Delete bots, given a list of ids
    """
    return Bot(collection_name="bots").delete(id)


@bot_blueprint.get("/bot/activate/{id}", tags=["bots"])
def activate(id: str):
    """
    Activate bot

    - Creates deal
    - If changes were made, it will override DB data
    - Because botId is received from endpoint, it will be a str not a PyObjectId
    """
    bot_instance = Bot(collection_name="bots")
    bot = bot_instance.activate(id)
    if bot:

        try:
            CreateDealController(bot, db_collection="bots").open_deal()
            return json_response_message("Successfully activated bot!")
        except BinanceErrors as error:
            logging.info(error)
            bot_instance.post_errors_by_id(id, error.message)
            return json_response_error(error.message)
        except BinbotErrors as error:
            logging.info(error)
            bot_instance.post_errors_by_id(id, error.message)
            return json_response_error(error.message)
        except Exception as error:
            bot_instance.post_errors_by_id(id, error)
            resp = json_response_error(f"Unable to activate bot: {error}")
            return resp
    else:
        return json_response_error("Bot not found.")


@bot_blueprint.delete("/bot/deactivate/{id}", tags=["bots"])
def deactivate(id: str):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    return Bot(collection_name="bots").deactivate(id)


@bot_blueprint.put("/bot/archive/{id}", tags=["bots"])
def archive(id: str):
    return Bot(collection_name="bots").put_archive(id)


@bot_blueprint.post("/bot/errors/{bot_id}", tags=["bots"])
def bot_errors(bot_id: str, bot_errors: ErrorsRequestBody):
    """
    POST errors to a bot

    - If error(s) is received from endpoint, get it from request body
    - Else use `post_errors_by_id` method for internal calls
    """
    request_body = bot_errors.model_dump(mode="python")
    bot_errors = request_body.get("errors", None)
    try:
        Bot(collection_name="bots").post_errors_by_id(bot_id, bot_errors)
    except Exception as error:
        return json_response_error(f"Error posting errors: {error}")
    return json_response_message("Errors posted successfully.")
