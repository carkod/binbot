from fastapi import APIRouter, Query, Request
from bots.controllers import Bot
from bots.schemas import BotSchema
from typing import List


paper_trading_blueprint = APIRouter()


@paper_trading_blueprint.get("/paper-trading", response_model=list[BotSchema], tags=["paper trading"])
def get(
    status: str | None = None,
    start_date: float | None = None,
    end_date: float | None = None,
    no_cooldown: bool = True,
):
    return Bot(collection_name="paper_trading").get(status, start_date, end_date, no_cooldown)


@paper_trading_blueprint.get("/paper-trading/{id}", tags=["paper trading"])
def get_one(id: str):
    return Bot(collection_name="paper_trading").get_one(id)


@paper_trading_blueprint.post("/paper-trading", tags=["paper trading"])
def create(bot_item: BotSchema):
    return Bot(collection_name="paper_trading").create(bot_item)


@paper_trading_blueprint.put("/paper-trading/{id}", tags=["paper trading"])
def edit(id: str, data: BotSchema):
    return Bot(collection_name="paper_trading").edit(id, data)


@paper_trading_blueprint.delete("/paper-trading", tags=["paper trading"])
def delete(id: List[str] = Query(...)):
    """
    Receives a list of `id=a1b2c3&id=b2c3d4`
    """
    return Bot(collection_name="paper_trading").delete(id)


@paper_trading_blueprint.get("/paper-trading/activate/{id}", tags=["paper trading"])
def activate(id: str):
    return Bot(collection_name="paper_trading").activate(id)


@paper_trading_blueprint.delete("/paper-trading/deactivate/{id}", tags=["paper trading"])
def deactivate(id: str):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    return Bot(collection_name="paper_trading").deactivate(id)
