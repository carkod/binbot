from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from account.controller import ConsolidatedAccounts
from user.models.user import UserTokenData
from user.services.auth import get_current_user
from exchange_apis.binance.assets import Assets
from account.schemas import (
    BalanceResponse,
    GainersLosersResponse,
    BalanceSeriesResponse,
    KucoinBalanceResponse,
)
from pybinbot import (
    BinanceErrors,
    BinbotErrors,
    LowBalanceCleanupError,
    MarginLoanNotFound,
    KucoinApi,
)
from tools.handle_error import json_response_error, json_response_message
from sqlmodel import Session
from databases.utils import get_session
from typing import Literal
from tools.config import Config

account_blueprint = APIRouter()
config = Config()


@account_blueprint.get("/balance", response_model=BalanceResponse, tags=["account"])
def get_balance(
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    accounts = ConsolidatedAccounts(session=session)
    data = accounts.get_balance()
    return {
        "data": data,
        "message": f"Successfully retrieved {accounts.autotrade_settings.exchange_id.name} balance.",
    }


@account_blueprint.get(
    "/kucoin-balance", response_model=KucoinBalanceResponse, tags=["account"]
)
def get_balance_by_type(
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
):
    accounts = ConsolidatedAccounts(session=session)
    data = accounts.get_kucoin_balances_by_type()
    return {
        "data": data,
        "message": f"Successfully retrieved {accounts.autotrade_settings.exchange_id.name} balance.",
    }


@account_blueprint.get("/store-balance", tags=["assets"])
def store_balance(session: Session = Depends(get_session)):
    """
    Internally used to store balance data,
    no need for authentication, as it also needs
    API keys for third party exchange APIs
    """
    accounts = ConsolidatedAccounts(session=session)
    data = accounts.store_balance()
    return {
        "data": data,
        "message": f"Successfully stored {accounts.autotrade_settings.exchange_id.name} balance.",
    }


@account_blueprint.get(
    "/gainers-losers", response_model=GainersLosersResponse, tags=["assets"]
)
async def retrieve_gainers_losers(session: Session = Depends(get_session)):
    return await Assets(session=session).retrieve_gainers_losers()


@account_blueprint.get(
    "/balance-series", response_model=BalanceSeriesResponse, tags=["assets"]
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


@account_blueprint.get("/clean", response_model=BalanceSeriesResponse, tags=["assets"])
def clean_balance(bypass: bool = False, session: Session = Depends(get_session)):
    try:
        accounts = ConsolidatedAccounts(session=session)
        accounts.clean_balance_assets(bypass=bypass)
        return json_response_message("Sucessfully cleaned balance.")
    except LowBalanceCleanupError as error:
        return json_response_error(f"Failed to clean balance: {error}")
    except BinanceErrors as error:
        return json_response_error(f"Failed to clean balance: {error.message}")


@account_blueprint.get(
    "/disable-isolated", response_model=BalanceSeriesResponse, tags=["account"]
)
def disable_isolated(session: Session = Depends(get_session)):
    return Assets(session=session).disable_isolated_accounts()


@account_blueprint.get("/isolated", tags=["account"])
def check_isolated_symbol(symbol: str, session: Session = Depends(get_session)):
    isolated_account = Assets(session=session).get_isolated_account(symbol)
    return isolated_account


@account_blueprint.get(
    "/one-click-liquidation/{bot_strategy}/{asset}", tags=["account"]
)
def one_click_liquidation(
    asset: str,
    bot_strategy: Literal["margin", "spot"],
    session: Session = Depends(get_session),
    _: UserTokenData = Depends(get_current_user),
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


@account_blueprint.get("/kucoin/balance/{asset}", tags=["account"])
def get_single_balance(asset: str, _: UserTokenData = Depends(get_current_user)):
    data = KucoinApi(
        key=config.kucoin_key,
        secret=config.kucoin_secret,
        passphrase=config.kucoin_passphrase,
    ).get_single_spot_balance(asset=asset)
    if data == 0:
        return HTTPException(
            status_code=404,
            detail=f"No balance found for asset {asset}",
        )

    return {
        "message": "Balance found!",
        "data": data,
    }
