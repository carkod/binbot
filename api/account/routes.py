import os

from api.account.account import Account
from api.account.assets import Assets
from flask import Blueprint

# initialization
os.environ["CORS_HEADERS"] = "Content-Type"

account_blueprint = Blueprint("account", __name__)

@account_blueprint.route("/btc-balance", methods=["GET"])
def get_balances_btc():
    return Assets().get_balances_btc()


@account_blueprint.route("/balance", methods=["GET"])
def get_balance():
    return Assets().get_value()


@account_blueprint.route("/balance/raw", methods=["GET"])
def raw_balance():
    return Assets().get_raw_balance()


@account_blueprint.route("/symbols", methods=["GET"])
def get_symbols():
    return Account().get_symbols_raw()


@account_blueprint.route("/symbols/raw", methods=["GET"])
def get_symbols_raw():
    return Account().get_symbols_raw()

@account_blueprint.route("/symbols/no-cannibal", methods=["GET"])
def get_no_cannibal_symbols():
    return Account().get_no_cannibal_symbols()

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


@account_blueprint.route("/balance/estimate", methods=["GET"])
def balance_estimated():
    return Assets().balance_estimate()

@account_blueprint.route("/balance/series", methods=["GET"])
def balance_series():
    return Assets().balance_series()

@account_blueprint.route("/pnl", methods=["GET"])
def get_pnl():
    return Assets().get_pnl()


@account_blueprint.route("/store-balance", methods=["GET"])
def store_balance():
    return Assets().store_balance()


@account_blueprint.route("/conversion", methods=["GET"])
def currency_conversion():
    return Assets().currency_conversion()
