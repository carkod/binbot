from fastapi import APIRouter

from api.account.account import Account
from api.account.assets import Assets
from api.auth import auth

router = APIRouter()


@router.get("/btc-balance")
def get_balances_btc():
    return Assets().get_balances_btc()


@router.get("/balance")
def get_balance():
    return Assets().get_value()


@router.get("/balance/raw")
def raw_balance():
    return Assets().get_raw_balance()


@router.get("/symbols")
def get_symbols():
    return Account().get_symbols()


@router.get("/symbols/no-cannibal")
def get_no_cannibal_symbols():
    return Account().get_no_cannibal_symbols()


@router.get("/symbol/<pair>")
def get_symbol_info(pair):
    return Account().get_symbol_info()


@router.get("/find-quote/<pair>")
def find_quote_asset(pair):
    return Account().find_quote_asset_json(pair)


@router.get("/find-base/<pair>")
def find_base_asset(pair):
    return Account().find_base_asset_json(pair)


@router.get("/ticker/{symbol}")
def ticker(symbol=None):
    return Account().ticker()


@router.get("/ticker24/{symbol}")
def ticker_24(symbol):
    return Account().ticker_24()


@router.get("/balance/estimate")
@auth.login_required
def balance_estimated():
    return Assets().balance_estimate()


@router.get("/balance/series")
@auth.login_required
def balance_series():
    return Assets().balance_series()


@router.get("/pnl")
@auth.login_required
def get_pnl():
    return Assets().get_pnl()


@router.get("/store-balance")
def store_balance():
    return Assets().store_balance()


@router.get("/conversion")
def currency_conversion():
    return Assets().currency_conversion()


@router.get("/hedge-gbp/<asset>")
@auth.login_required
def buy_gbp_balance(asset):
    return Assets().buy_gbp_balance()
