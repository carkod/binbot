import os

from flask import Blueprint
from api.account.models import Account, Assets


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

@account_blueprint.route("/ticker", defaults={'symbol': None})
@account_blueprint.route("/ticker/<symbol>", methods=["GET"])
def ticker(symbol=None):
    return Account().ticker()

@account_blueprint.route("/ticker24/<symbol>", methods=["GET"])
def ticker_24(symbol):
    return Account().ticker_24()

@account_blueprint.route("/update-assets", methods=["GET"])
def store_balance():
    return Assets().get_btc_balance()

@account_blueprint.route("/assets", defaults={'interval': None})
@account_blueprint.route("/assets/<interval>", methods=["GET"])
def get_value(interval):
    return Assets().get_value()

@account_blueprint.route("/pnl", methods=["GET"])
def get_pnl():
    return Assets().get_pnl()
