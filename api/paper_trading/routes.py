from flask import Blueprint
from api.bots.controllers import Bot
from api.auth import auth
from api.paper_trading.controllers import PaperTradingController

paper_trading_blueprint = Blueprint("paper-trading", __name__)


@paper_trading_blueprint.route("/paper-trading", methods=["GET"])
@auth.login_required
def get():
    return Bot(collection_name="paper_trading").get()

@paper_trading_blueprint.route("/paper-trading/<id>", methods=["GET"])
@auth.login_required
def get_one(id):
    return Bot(collection_name="paper_trading").get_one()

@paper_trading_blueprint.route("/paper-trading", methods=["POST"])
@auth.login_required
def create():
    return Bot(collection_name="paper_trading").create()

@paper_trading_blueprint.route("/paper-trading/<id>", methods=["PUT"])
@auth.login_required
def edit(id):
    return Bot(collection_name="paper_trading").edit()


@paper_trading_blueprint.route("/paper-trading", methods=["DELETE"])
@auth.login_required
def delete():
    return Bot(collection_name="paper_trading").delete()


@paper_trading_blueprint.route("/paper-trading/activate/<botId>", methods=["GET"])
@auth.login_required
def activate(botId):
    return PaperTradingController().activate()


@paper_trading_blueprint.route("/paper-trading/deactivate/<id>", methods=["DELETE"])
@auth.login_required
def deactivate(id):
    """
    Deactivation means closing all deals and selling to GBP
    Otherwise losses will be incurred
    """
    return PaperTradingController().deactivate()
