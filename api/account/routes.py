from fastapi import APIRouter
from datetime import datetime, timedelta
from account.account import Account
from account.assets import Assets
from account.schemas import (
    BalanceResponse,
    GainersLosersResponse,
    BalanceSeriesResponse,
    GetMarketDominationResponse,
    MarketDominationResponse,
    MarketDominationSeries,
)
from tools.exceptions import BinanceErrors, LowBalanceCleanupError
from tools.handle_error import json_response, json_response_error, json_response_message

account_blueprint = APIRouter()


@account_blueprint.get("/balance/raw", response_model=BalanceResponse, tags=["account"])
def raw_balance():
    data = Assets().get_raw_balance()
    return json_response({"data": data}) 


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


@account_blueprint.get("/balance/estimate", tags=["assets"])
def balance_estimated():
    try:
        balance = Assets().balance_estimate()
        if balance:
            return json_response({"data": balance, "message": "Successfully retrieved estimated balance."})
    except BinanceErrors as error:
        return json_response_error(f"Failed to estimate balance: {error}")    


@account_blueprint.get("/balance/series", tags=["assets"])
def balance_series():
    return Assets().balance_series()


@account_blueprint.get("/pnl", tags=["assets"])
def get_pnl():
    return Assets().get_pnl()


@account_blueprint.get("/store-balance", tags=["assets"])
def store_balance():
    try:
        Assets().store_balance()
        response = json_response_message("Successfully stored balance.")
    except Exception as error:
        response = json_response_error(f"Failed to store balance: {error}")
    return response


@account_blueprint.get(
    "/gainers-losers", response_model=GainersLosersResponse, tags=["assets"]
)
async def retrieve_gainers_losers():
    return await Assets().retrieve_gainers_losers()


@account_blueprint.get(
    "/balance-series", response_model=BalanceSeriesResponse, tags=["assets"]
)
async def get_balance_series():
    today = datetime.now()
    month_ago = today - timedelta(30)
    return await Assets().get_balance_series(
        start_date=datetime.timestamp(month_ago), end_date=datetime.timestamp(today)
    )


@account_blueprint.get("/clean", response_model=BalanceSeriesResponse, tags=["assets"])
def clean_balance(bypass: bool = False):

    try:
        Assets().clean_balance_assets(bypass=bypass)
        return json_response_message("Sucessfully cleaned balance.")
    except LowBalanceCleanupError as error:
        return json_response_error(f"Failed to clean balance: {error}")
    except BinanceErrors as error:
        return json_response_error(f"Failed to clean balance: {error}")

@account_blueprint.get("/fiat/available", response_model=BalanceSeriesResponse, tags=["assets"])
def total_balance():
    """
    Total USDC in balance
    Calculated by Binance
    """
    total_fiat = Assets().get_available_fiat()
    return json_response({"data": total_fiat})

@account_blueprint.get("/fiat", response_model=BalanceSeriesResponse, tags=["assets"])
def total_balance():
    """
    Total USDC in balance
    Calculated by Binance
    """
    total_fiat = Assets().get_total_fiat()
    return json_response({"data": total_fiat})

@account_blueprint.get(
    "/disable-isolated", response_model=BalanceSeriesResponse, tags=["assets"]
)
def disable_isolated():
    return Assets().disable_isolated_accounts()

@account_blueprint.get("/isolated", tags=["assets"])
def check_isolated_symbol(symbol: str):
    isolated_account = Assets().get_isolated_account(symbol)
    return isolated_account


@account_blueprint.get("/one-click-liquidation/{asset}", tags=["assets"])
def one_click_liquidation(asset):
    return Assets().one_click_liquidation(asset)


@account_blueprint.get(
    "/market-domination", tags=["assets"], response_model=MarketDominationResponse
)
def market_domination(size: int = 7):

    data = Assets().get_market_domination(size)
    market_domination_series = MarketDominationSeries()

    try:
        for item in data:
            gainers_percent = 0
            losers_percent = 0
            gainers_count = 0
            losers_count = 0
            total_volume = 0
            if "data" in item:
                for crypto in item["data"]:
                    if float(crypto['priceChangePercent']) > 0:
                        gainers_percent += float(crypto['volume'])
                        gainers_count += 1

                    if float(crypto['priceChangePercent']) < 0:
                        losers_percent += abs(float(crypto['volume']))
                        losers_count += 1

                    if float(crypto['volume']) > 0:
                        total_volume += float(crypto['volume']) * float(crypto['price'])

            market_domination_series.dates.append(item["time"])
            market_domination_series.gainers_percent.append(gainers_percent)
            market_domination_series.losers_percent.append(losers_percent)
            market_domination_series.gainers_count.append(gainers_count)
            market_domination_series.losers_count.append(losers_count)
            market_domination_series.total_volume.append(total_volume)

        market_domination_series.dates = market_domination_series.dates[-size:]
        market_domination_series.gainers_percent = (
            market_domination_series.gainers_percent[-size:]
        )
        market_domination_series.losers_percent = (
            market_domination_series.losers_percent[-size:]
        )
        market_domination_series.gainers_count = market_domination_series.gainers_count[
            -size:
        ]
        market_domination_series.losers_count = market_domination_series.losers_count[
            -size:
        ]
        market_domination_series.total_volume = market_domination_series.total_volume[
            -size:
        ]

        data = market_domination_series.model_dump(mode="json")

        return json_response(
            {
                "data": data,
                "message": "Successfully retrieved market domination data.",
                "error": 0,
            }
        )
    except Exception as error:
        return json_response_error(
            f"Failed to retrieve market domination data: {error}"
        )


@account_blueprint.get(
    "/store-market-domination",
    tags=["assets"],
    response_model=GetMarketDominationResponse,
)
def store_market_domination():
    return Assets().store_market_domination()
