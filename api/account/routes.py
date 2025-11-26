from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
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

from databases.utils import get_session
from databases.crud.balances_crud import BalancesCrud
from typing import Literal
from user.services.auth import decode_access_token

account_blueprint = APIRouter()


@account_blueprint.get(
    "/balance/raw",
    dependencies=[Depends(decode_access_token)],
    response_model=BalanceResponse,
    tags=["account"],
)
def raw_balance(session: Session = Depends(get_session)):
    data = Assets(session=session).get_raw_balance()
    return json_response({"data": data})


@account_blueprint.get(
    "/balance/estimate",
    dependencies=[Depends(decode_access_token)],
    tags=["assets"],
)
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


@account_blueprint.get(
    "/pnl",
    dependencies=[Depends(decode_access_token)],
    tags=["assets"],
)
def get_pnl(days: int = 7, session: Session = Depends(get_session)):
    current_time = datetime.now()
    start = current_time - timedelta(days=days)
    ts = int(start.timestamp())
    end_ts = int(current_time.timestamp())
    data = BalancesCrud(session=session).query_balance_series(ts, end_ts)

    resp = json_response({"data": data})
    return resp


@account_blueprint.get(
    "/store-balance",
    dependencies=[Depends(decode_access_token)],
    tags=["assets"],
)
def store_balance(session: Session = Depends(get_session)):
    try:
        Assets(session=session).store_balance()
        response = json_response_message("Successfully stored balance.")
    except Exception as error:
        response = json_response_error(f"Failed to store balance: {error}")
    return response


@account_blueprint.get(
    "/gainers-losers",
    dependencies=[Depends(decode_access_token)],
    response_model=GainersLosersResponse,
    tags=["assets"],
)
async def retrieve_gainers_losers(session: Session = Depends(get_session)):
    return await Assets(session=session).retrieve_gainers_losers()


@account_blueprint.get(
    "/balance-series",
    dependencies=[Depends(decode_access_token)],
    response_model=BalanceSeriesResponse,
    tags=["assets"],
)
def get_portfolio_performance(session: Session = Depends(get_session)):
    today = datetime.now()
    month_ago = today - timedelta(30)
    start_date = int(datetime.timestamp(month_ago) * 1000)
    end_date = int(datetime.timestamp(today) * 1000)
    data = Assets(session=session).map_balance_with_benchmark(
        start_date=start_date, end_date=end_date
    )
    return BalanceSeriesResponse(
        data=data, message="Successfully retrieved balance series."
    )


@account_blueprint.get(
    "/clean",
    dependencies=[Depends(decode_access_token)],
    response_model=BalanceSeriesResponse,
    tags=["assets"],
)
def clean_balance(bypass: bool = False, session: Session = Depends(get_session)):
    try:
        Assets(session=session).clean_balance_assets(bypass=bypass)
        return json_response_message("Sucessfully cleaned balance.")
    except LowBalanceCleanupError as error:
        return json_response_error(f"Failed to clean balance: {error}")
    except BinanceErrors as error:
        return json_response_error(f"Failed to clean balance: {error.message}")


@account_blueprint.get(
    "/fiat/available",
    dependencies=[Depends(decode_access_token)],
    response_model=BalanceSeriesResponse,
    tags=["account"],
)
def fiat_available(session: Session = Depends(get_session)):
    """
    Total USDC in balance
    Calculated by Binance
    """
    total_fiat = Assets(session=session).get_available_fiat()
    return json_response({"data": total_fiat})


@account_blueprint.get(
    "/fiat",
    dependencies=[Depends(decode_access_token)],
    response_model=BalanceSeriesResponse,
    tags=["account"],
)
def fiat(session: Session = Depends(get_session)):
    """
    Total USDC in balance
    Calculated by Binance
    """
    total_fiat = Assets(session=session).get_total_fiat()
    return json_response({"data": total_fiat})


@account_blueprint.get(
    "/disable-isolated",
    dependencies=[Depends(decode_access_token)],
    response_model=BalanceSeriesResponse,
    tags=["account"],
)
def disable_isolated(session: Session = Depends(get_session)):
    return Assets(session=session).disable_isolated_accounts()


@account_blueprint.get(
    "/isolated",
    dependencies=[Depends(decode_access_token)],
    tags=["account"],
)
def check_isolated_symbol(symbol: str, session: Session = Depends(get_session)):
    isolated_account = Assets(session=session).get_isolated_account(symbol)
    return isolated_account


@account_blueprint.get(
    "/one-click-liquidation/{bot_strategy}/{asset}",
    dependencies=[Depends(decode_access_token)],
    tags=["account"],
)
def one_click_liquidation(
    asset: str,
    bot_strategy: Literal["margin", "spot"],
    session: Session = Depends(get_session),
):
    try:
        liquidated = Assets(session=session).one_click_liquidation(
            pair=asset, bot_strategy=bot_strategy
        )
        if not liquidated:
            raise HTTPException(
                status_code=404,
                detail=f"Could not liquidate {asset} that doesn't exist.",
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
