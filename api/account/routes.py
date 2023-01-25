from fastapi import APIRouter

from account.account import Account
from account.assets import Assets
from account.schemas import BalanceResponse, GainersLosersResponse
from account.margin import MarginAccount
from account.schemas import EstimatedBalancesResponse

account_blueprint = APIRouter()


@account_blueprint.get("/balance/raw", response_model=BalanceResponse, tags=["account"])
def raw_balance():
    return Assets().get_raw_balance()


@account_blueprint.get("/symbols", tags=["account"])
def get_symbols():
    return Account().get_symbols()


@account_blueprint.get("/symbols/no-cannibal", tags=["account"])
def get_no_cannibal_symbols():
    return Account().get_no_cannibal_symbols()


@account_blueprint.get("/symbol/{pair}", tags=["account"])
@account_blueprint.get("/symbol", tags=["account"])
def get_symbol_info(pair):
    return Account().get_symbol_info(pair)


@account_blueprint.get("/find-quote/{pair}", tags=["account"])
def find_quote_asset(pair):
    return Account().find_quote_asset_json(pair)


@account_blueprint.get("/find-base/{pair}", tags=["account"])
def find_base_asset(pair):
    return Account().find_base_asset_json(pair)


@account_blueprint.get("/ticker/{pair}", tags=["account"])
@account_blueprint.get("/ticker", tags=["account"])
def ticker(pair: str | None = None):
    return Account().ticker(pair)


@account_blueprint.get("/ticker24/{pair}", tags=["account"])
@account_blueprint.get("/ticker24", tags=["account"])
def ticker_24(pair=None):
    return Account().ticker_24(symbol=pair)


@account_blueprint.get("/balance/estimate", tags=["account"])
async def balance_estimated():
    return Assets().balance_estimate()


@account_blueprint.get("/balance/series", tags=["account"])
def balance_series():
    return Assets().balance_series()


@account_blueprint.get("/pnl", tags=["account"])
def get_pnl():
    return Assets().get_pnl()


@account_blueprint.get("/store-balance", tags=["account"])
def store_balance():
    return Assets().store_balance()


@account_blueprint.get("/gainers-losers", response_model=GainersLosersResponse, tags=["account"])
async def retrieve_gainers_losers():
    return await Assets().retrieve_gainers_losers()

@account_blueprint.get("/balance/margin", response_model=EstimatedBalancesResponse, tags=["margin"])
def margin_balance_estimate():
    return MarginAccount().margin_balance_estimate()
