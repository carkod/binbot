from fastapi import APIRouter, Depends
from pybinbot import BinanceErrors, KucoinApi, KucoinFutures
from tools.config import Config
from tools.handle_error import json_response_error
from user.models.user import UserTokenData
from user.services.auth import get_current_user

config = Config()
kucoin_order_blueprint = APIRouter()


@kucoin_order_blueprint.get("/futures/position/{symbol}", tags=["orders"])
def get_futures_position(symbol: str, _: UserTokenData = Depends(get_current_user)):
    try:
        data = KucoinFutures(
            key=config.kucoin_key,
            secret=config.kucoin_secret,
            passphrase=config.kucoin_passphrase,
        ).get_futures_position(symbol=symbol)
        return {
            "message": "Position found!",
            "data": data,
        }
    except ValueError as error:
        return json_response_error(error.args[0])
    except BinanceErrors as error:
        return json_response_error(error.message)


@kucoin_order_blueprint.get("/futures/{order_id}", tags=["orders"])
def get_futures_orders(order_id: str, _: UserTokenData = Depends(get_current_user)):
    try:
        data = KucoinFutures(
            key=config.kucoin_key,
            secret=config.kucoin_secret,
            passphrase=config.kucoin_passphrase,
        ).retrieve_order(order_id)
        return {
            "message": "Order found!",
            "data": data,
        }
    except ValueError as error:
        return json_response_error(error.args[0])
    except BinanceErrors as error:
        return json_response_error(error.message)


@kucoin_order_blueprint.get("/{symbol}/{order_id}", tags=["orders"])
def get_order_by_id(
    symbol: str, order_id: str, _: UserTokenData = Depends(get_current_user)
):
    """
    Get a specific Kucoin SPOT order by symbol and order ID.
    """
    try:
        data = KucoinApi(
            key=config.kucoin_key,
            secret=config.kucoin_secret,
            passphrase=config.kucoin_passphrase,
        ).get_order(symbol=symbol, order_id=order_id)
        return {
            "message": "Order found!",
            "data": data,
        }
    except ValueError as error:
        return json_response_error(error.args[0])
    except BinanceErrors as error:
        return json_response_error(error.message)
