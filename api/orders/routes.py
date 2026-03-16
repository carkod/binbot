from fastapi import APIRouter, Depends
from pybinbot import KucoinApi, BinanceErrors
from user.models.user import UserTokenData
from user.services.auth import get_current_user
from tools.handle_error import json_response, json_response_error
from exchange_apis.binance.orders import BinanceOrderController
from orders.schemas import OrderParams
from tools.config import Config

config = Config()
order_blueprint = APIRouter()


@order_blueprint.post("/buy", tags=["orders"])
def create_buy_order(item: OrderParams, _: UserTokenData = Depends(get_current_user)):
    return BinanceOrderController().buy_order(symbol=item.pair, qty=item.qty)


@order_blueprint.post("/sell", tags=["orders"])
def create_sell_order(item: OrderParams, _: UserTokenData = Depends(get_current_user)):
    return BinanceOrderController().sell_order(symbol=item.pair, qty=item.qty)


@order_blueprint.delete("/close/{symbol}/{orderid}", tags=["orders"])
def delete_order(symbol, orderid, _: UserTokenData = Depends(get_current_user)):
    try:
        data = BinanceOrderController().delete_order(symbol, orderid)
        resp = json_response({"message": "Order deleted!", "data": data})
    except BinanceErrors as error:
        resp = json_response_error(error.message)
        pass

    return resp


@order_blueprint.get("/margin/sell/{symbol}/{qty}", tags=["orders"])
def margin_sell(symbol, qty, _: UserTokenData = Depends(get_current_user)):
    return BinanceOrderController().sell_margin_order(symbol, qty)


@order_blueprint.get("/all-orders", tags=["orders"])
def get_all_orders(
    symbol,
    order_id: str | None = None,
    start_time=None,
    _: UserTokenData = Depends(get_current_user),
):
    try:
        data = BinanceOrderController().get_all_orders(
            symbol, order_id=order_id, start_time=start_time
        )
        return json_response({"message": "Orders found!", "data": data})
    except ValueError as error:
        return json_response_error(error.args[0])
    except BinanceErrors as error:
        return json_response_error(error.message)


@order_blueprint.get("/kucoin/{symbol}/{order_id}", tags=["orders"])
def get_order_by_id(
    symbol: str, order_id: str, _: UserTokenData = Depends(get_current_user)
):
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
