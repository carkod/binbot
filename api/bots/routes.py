from fastapi import APIRouter
from api.bots.controllers import Bot

bot_blueprint = APIRouter()


@bot_blueprint.get("/bot")
def get():
    return Bot(collection_name="bots").get()


@bot_blueprint.get("/bot/<id>")
def get_one(id: str):
    return Bot(collection_name="bots").get_one(id)


@bot_blueprint.post("/bot")
def create(bot):
    return Bot(collection_name="bots").create(bot)


@bot_blueprint.put("/bot/<id>")
def edit(id):
    return Bot(collection_name="bots").edit()


@bot_blueprint.delete("/bot")
def delete():
    return Bot(collection_name="bots").delete()


@bot_blueprint.get("/bot/activate/<botId>")
def activate(botId):
    return Bot(collection_name="bots").activate()


@bot_blueprint.delete("/bot/deactivate/<id>")
def deactivate(id):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    return Bot(collection_name="bots").deactivate()


@bot_blueprint.put("/bot/archive/<id>")
def archive(id):
    return Bot(collection_name="bots").put_archive()
