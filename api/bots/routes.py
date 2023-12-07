from fastapi import APIRouter, Query
from flask import request
from bots.controllers import Bot
from bots.schemas import BotSchema, BotListResponse, ErrorsRequestBody
from typing import List

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
def get_one(id: str):
    return Bot(collection_name="bots").get_one(id)


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
    return Bot(collection_name="bots").activate(id)


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
    request_body = bot_errors.dict()
    bot_errors = request_body.get("errors", None)
    return Bot(collection_name="bots").post_errors_by_id(bot_id, bot_errors)
