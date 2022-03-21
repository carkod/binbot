from flask import Blueprint
from api.paper_trading.models import Bot

paper_trading_blueprint = Blueprint("paper-trading", __name__)


@paper_trading_blueprint.route("/paper-trading", methods=["GET"])
@paper_trading_blueprint.route("/paper-trading/<id>", methods=["GET"])
def get():
    return Bot().get()


@paper_trading_blueprint.route("/paper-trading", methods=["POST"])
def create():
    return Bot().create()


@paper_trading_blueprint.route("/paper-trading/<id>", methods=["PUT"])
def edit(id):
    return Bot().edit()


@paper_trading_blueprint.route("/paper-trading", methods=["DELETE"])
def delete():
    return Bot().delete()


@paper_trading_blueprint.route("/paper-trading/activate/<botId>", methods=["GET"])
def activate(botId):
    return Bot().activate()


@paper_trading_blueprint.route("/paper-trading/deactivate/<id>", methods=["DELETE"])
def deactivate(id):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    return Bot().deactivate()
