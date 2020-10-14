from flask import Blueprint
from main.deals.models import Deal


deal_blueprint = Blueprint("deal", __name__)
# @token_required
@deal_blueprint.route("/open/<id>", methods=["GET"])
def get():
    return Deal().get_balances()

@deal_blueprint.route("/close/<id>", methods=["GET"])
def getAuth():
    return Deal().get_balances()
