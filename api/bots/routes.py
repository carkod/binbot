from flask import Blueprint
from api.bots.models import Bot

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


@bot_blueprint.route("/<id>", methods=["PUT"])
def edit(id):
    return Bot().edit()


@bot_blueprint.route("/<id>", methods=["DELETE"])
def delete(id):
    return Bot().delete()

@bot_blueprint.route("/activate/<botId>", methods=["GET"])
def activate(botId):
    return Bot().activate()

@bot_blueprint.route("/close/<id>", methods=["DELETE"])
def close(id):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    return Bot().deactivate()

@bot_blueprint.route("/archive/<id>", methods=["PUT"])
def archive(id):
    return Bot().put_archive()
