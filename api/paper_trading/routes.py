from fastapi import APIRouter

from api.bots.controllers import Bot

paper_trading_blueprint = APIRouter()


@paper_trading_blueprint.get("/paper-trading")
def get():
    return Bot(collection_name="paper_trading").get()


@paper_trading_blueprint.get("/paper-trading/<id>")
def get_one(id):
    return Bot(collection_name="paper_trading").get_one()


@paper_trading_blueprint.post("/paper-trading")
def create():
    return Bot(collection_name="paper_trading").create()


@paper_trading_blueprint.put("/paper-trading/<id>")
def edit(id):
    return Bot(collection_name="paper_trading").edit()


@paper_trading_blueprint.delete("/paper-trading")
def delete():
    return Bot(collection_name="paper_trading").delete()


@paper_trading_blueprint.get("/paper-trading/activate/<botId>")
def activate(botId):
    return Bot(collection_name="paper_trading").activate()


@paper_trading_blueprint.delete("/paper-trading/deactivate/<id>")
def deactivate(id):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    return Bot(collection_name="paper_trading").deactivate()
