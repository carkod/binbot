import os

from flask import Blueprint
from main.account.models import Account, Balances


# initialization
os.environ['CORS_HEADERS'] = 'Content-Type'

account_blueprint = Blueprint("account", __name__)
# @token_required


@account_blueprint.route("/", methods=["GET"])
def get():
    return Account().get_balances()

@account_blueprint.route("/balance", methods=["GET"])
def getAuth():
    return Account().get_balances()

@account_blueprint.route("/symbols/", methods=["GET"])
def get_symbols():
    return Account().get_symbols()

@account_blueprint.route("/symbol/<pair>", methods=["GET"])
def get_symbol_info(pair):
    return Account().get_symbol_info()

@account_blueprint.route("/update-balance", methods=["GET"])
def store_balance():
    return Balances().store_balance()

@account_blueprint.route("/portfolio/", methods=["GET"])
def get_value():
    return Balances().get_value()
