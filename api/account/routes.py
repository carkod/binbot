import os

from flask import Blueprint
from api.account.account import Account
from api.account.assets import Assets

# initialization
os.environ["CORS_HEADERS"] = "Content-Type"

account_blueprint = Blueprint("account", __name__)
# @token_required


@account_blueprint.route("/btc-balance", methods=["GET"])
def get_balances_btc():
    return Assets().get_balances_btc()


@account_blueprint.route("/balance", methods=["GET"])
def raw_balance():
    return Assets().get_raw_balance()


@account_blueprint.route("/balance/binbot", methods=["GET"])
def binbot_balance():
    return Assets().get_binbot_balance()

@account_blueprint.route("/symbols/", methods=["GET"])
def get_symbols():
    return Account().get_symbols()


@account_blueprint.route("/symbol/<pair>", methods=["GET"])
def get_symbol_info(pair):
    return Account().get_symbol_info()


@account_blueprint.route("/find-quote/<pair>", methods=["GET"])
def find_quote_asset(pair):
    return Account().find_quote_asset_json(pair)


@account_blueprint.route("/find-base/<pair>", methods=["GET"])
def find_base_asset(pair):
    return Account().find_base_asset_json(pair)


@account_blueprint.route("/ticker", defaults={"symbol": None})
@account_blueprint.route("/ticker/<symbol>", methods=["GET"])
def ticker(symbol=None):
    return Account().ticker()


@account_blueprint.route("/ticker24/<symbol>", methods=["GET"])
def ticker_24(symbol):
    return Account().ticker_24()


@account_blueprint.route("/assets", defaults={"interval": None})
@account_blueprint.route("/assets/<interval>", methods=["GET"])
def get_value(interval):
    return Assets().get_value()


@account_blueprint.route("/pnl", methods=["GET"])
def get_pnl():
    return Assets().get_pnl()


@account_blueprint.route("/gbp", methods=["GET"])
def get_gbp_balance():
    return Account().get_gbp_balance()

@account_blueprint.route("/store-balance", methods=["GET"])
def store_balance():
    return Assets().store_balance()
