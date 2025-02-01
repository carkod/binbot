from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from account.account import Account
from account.assets import Assets
from account.schemas import (
    BalanceResponse,
    GainersLosersResponse,
    BalanceSeriesResponse,
)
from tools.exceptions import (
    BinanceErrors,
    BinbotErrors,
    LowBalanceCleanupError,
    MarginLoanNotFound,
)
from tools.handle_error import json_response, json_response_error, json_response_message
from sqlmodel import Session
from database.utils import get_session
from database.balances_crud import BalancesCrud


account_blueprint = APIRouter()


@account_blueprint.get("/balance/raw", response_model=BalanceResponse, tags=["account"])
def raw_balance(session: Session = Depends(get_session)):
    data = Assets(session=session).get_raw_balance()
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


@account_blueprint.get("/balance/estimate", tags=["assets"])
def balance_estimated(session: Session = Depends(get_session)):
    try:
        balance = Assets(session=session).balance_estimate()
        if balance:
            return json_response(
                {
                    "data": balance,
                    "message": "Successfully retrieved estimated balance.",
                }
            )
    except BinanceErrors as error:
        return json_response_error(f"Failed to estimate balance: {error}")


@account_blueprint.get("/pnl", tags=["assets"])
def get_pnl(days: int = 7, session: Session = Depends(get_session)):
    current_time = datetime.now()
    start = current_time - timedelta(days=days)
    ts = int(start.timestamp())
    end_ts = int(current_time.timestamp())
    data = BalancesCrud(session=session).query_balance_series(ts, end_ts)

    resp = json_response({"data": data})
    return resp


@account_blueprint.get("/store-balance", tags=["assets"])
def store_balance(session: Session = Depends(get_session)):
    try:
        Assets(session=session).store_balance()
        response = json_response_message("Successfully stored balance.")
    except Exception as error:
        response = json_response_error(f"Failed to store balance: {error}")
    return response


@account_blueprint.get(
    "/gainers-losers", response_model=GainersLosersResponse, tags=["assets"]
)
async def retrieve_gainers_losers(session: Session = Depends(get_session)):
    return await Assets(session=session).retrieve_gainers_losers()


@account_blueprint.get(
    "/balance-series", response_model=BalanceSeriesResponse, tags=["assets"]
)
async def get_balance_series(session: Session = Depends(get_session)):
    today = datetime.now()
    month_ago = today - timedelta(30)
    start_date = int(datetime.timestamp(month_ago) * 1000)
    end_date = int(datetime.timestamp(today) * 1000)
    return await Assets(session=session).get_balance_series(
        start_date=start_date, end_date=end_date
    )


@account_blueprint.get("/clean", response_model=BalanceSeriesResponse, tags=["assets"])
def clean_balance(bypass: bool = False, session: Session = Depends(get_session)):
    try:
        Assets(session=session).clean_balance_assets(bypass=bypass)
        return json_response_message("Sucessfully cleaned balance.")
    except LowBalanceCleanupError as error:
        return json_response_error(f"Failed to clean balance: {error}")
    except BinanceErrors as error:
        return json_response_error(f"Failed to clean balance: {error}")


@account_blueprint.get(
    "/fiat/available", response_model=BalanceSeriesResponse, tags=["assets"]
)
def fiat_available(session: Session = Depends(get_session)):
    """
    Total USDC in balance
    Calculated by Binance
    """
    total_fiat = Assets(session=session).get_available_fiat()
    return json_response({"data": total_fiat})


@account_blueprint.get("/fiat", response_model=BalanceSeriesResponse, tags=["assets"])
def fiat(session: Session = Depends(get_session)):
    """
    Total USDC in balance
    Calculated by Binance
    """
    total_fiat = Assets(session=session).get_total_fiat()
    return json_response({"data": total_fiat})


@account_blueprint.get(
    "/disable-isolated", response_model=BalanceSeriesResponse, tags=["assets"]
)
def disable_isolated(session: Session = Depends(get_session)):
    return Assets(session=session).disable_isolated_accounts()


@account_blueprint.get("/isolated", tags=["assets"])
def check_isolated_symbol(symbol: str, session: Session = Depends(get_session)):
    isolated_account = Assets(session=session).get_isolated_account(symbol)
    return isolated_account


@account_blueprint.get("/one-click-liquidation/{market}/{asset}", tags=["assets"])
def one_click_liquidation(
    asset: str, market: str = "margin", session: Session = Depends(get_session)
):
    try:
        liquidated = Assets(session=session).one_click_liquidation(asset, market)
        if not liquidated:
            raise HTTPException(
                status_code=404, detail="Could not liquidate asset that doesn't exist."
            )
        return json_response_message(f"Successfully liquidated {asset}")
    except MarginLoanNotFound as error:
        return json_response_message(
            f"{error}. Successfully cleared isolated pair {asset}"
        )
    except BinanceErrors as error:
        return json_response_error(f"Error liquidating {asset}: {error.message}")

    except BinbotErrors as error:
        return json_response_error(f"Error liquidating {asset}: {error.message}")
