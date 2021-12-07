from flask import Blueprint
from api.bots.models import Bot
from api.auth import auth

bot_blueprint = Blueprint("bot", __name__)


@bot_blueprint.route("/bot", methods=["GET"])
@auth.login_required
def get():
    return Bot().get()


@bot_blueprint.route("/bot/<id>", methods=["GET"])
@auth.login_required
def get_one(id):
    return Bot().get_one()


@bot_blueprint.route("/bot", methods=["POST"])
@auth.login_required
def create():
    return Bot().create()


@bot_blueprint.route("/bot/<id>", methods=["PUT"])
@auth.login_required
def edit(id):
    return Bot().edit()


@bot_blueprint.route("/bot", methods=["DELETE"])
@auth.login_required
def delete():
    return Bot().delete()


@bot_blueprint.route("/bot/activate/<botId>", methods=["GET"])
@auth.login_required
def activate(botId):
    return Bot().activate()


@bot_blueprint.route("/bot/close/<id>", methods=["DELETE"])
@auth.login_required
def close(id):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    return Bot().deactivate()


@bot_blueprint.route("/bot/archive/<id>", methods=["PUT"])
@auth.login_required
def archive(id):
    return Bot().put_archive()
