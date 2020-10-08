from flask import Blueprint
from main.bots.models import Bot

bot_blueprint = Blueprint("bot", __name__)


@bot_blueprint.route("/", methods=["GET"])
def get():
    return Bot().get()


@bot_blueprint.route("/<id>", methods=["GET"])
def get_one(id):
    return Bot().get_one()


@bot_blueprint.route("/", methods=["POST"])
def create():
    return Bot().create()


@bot_blueprint.route("/", methods=["PUT"])
def edit():
    return Bot().edit()


@bot_blueprint.route("/<id>", methods=["DELETE"])
def delete(id):
    return Bot().delete(id)


@bot_blueprint.route("/activate/<botId>", methods=["GET"])
def activate(botId):
    return Bot().activate()


@bot_blueprint.route("/deactivate/<botId>", methods=["GET"])
def deactivate(botId):
    return Bot().deactivate()
