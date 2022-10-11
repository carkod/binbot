from flask import Blueprint
from api.bots.controllers import Bot
from api.auth import auth

bot_blueprint = Blueprint("bot", __name__)


@bot_blueprint.route("/bot", methods=["GET"])
@auth.login_required
def get():
    return Bot(collection_name="bots").get()


@bot_blueprint.route("/bot/<id>", methods=["GET"])
@auth.login_required
def get_one(id):
    return Bot(collection_name="bots").get_one()


@bot_blueprint.route("/bot", methods=["POST"])
@auth.login_required
def create():
    return Bot(collection_name="bots").create()


@bot_blueprint.route("/bot/<id>", methods=["PUT"])
@auth.login_required
def edit(id):
    return Bot(collection_name="bots").edit()


@bot_blueprint.route("/bot", methods=["DELETE"])
@auth.login_required
def delete():
    return Bot(collection_name="bots").delete()


@bot_blueprint.route("/bot/activate/<botId>", methods=["GET"])
@auth.login_required
def activate(botId):
    return Bot(collection_name="bots").activate()


@bot_blueprint.route("/bot/deactivate/<id>", methods=["DELETE"])
@auth.login_required
def deactivate(id):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    return Bot(collection_name="bots").deactivate()


@bot_blueprint.route("/bot/archive/<id>", methods=["PUT"])
@auth.login_required
def archive(id):
    return Bot(collection_name="bots").put_archive()
