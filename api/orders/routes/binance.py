from exchange_apis.binance.orders import BinanceOrderController
from fastapi import APIRouter, Depends
from orders.schemas import OrderParams
from pybinbot import BinanceErrors
from tools.config import Config
from tools.handle_error import json_response, json_response_error
from user.models.user import UserTokenData
from user.services.auth import get_current_user

config = Config()
binance_order_blueprint = APIRouter()


@binance_order_blueprint.post("/buy", tags=["orders"])
def create_buy_order(item: OrderParams, _: UserTokenData = Depends(get_current_user)):
    return BinanceOrderController().buy_order(symbol=item.pair, qty=item.qty)


@binance_order_blueprint.post("/sell", tags=["orders"])
def create_sell_order(item: OrderParams, _: UserTokenData = Depends(get_current_user)):
    return BinanceOrderController().sell_order(symbol=item.pair, qty=item.qty)


@binance_order_blueprint.delete("/close/{symbol}/{orderid}", tags=["orders"])
def delete_order(symbol, orderid, _: UserTokenData = Depends(get_current_user)):
    try:
        data = BinanceOrderController().delete_order(symbol, orderid)
        resp = json_response({"message": "Order deleted!", "data": data})
    except BinanceErrors as error:
        resp = json_response_error(error.message)
        pass

    return resp


@binance_order_blueprint.get("/margin/sell/{symbol}/{qty}", tags=["orders"])
def margin_sell(symbol, qty, _: UserTokenData = Depends(get_current_user)):
    return BinanceOrderController().sell_margin_order(symbol, qty)


@binance_order_blueprint.get("/all-orders", tags=["orders"])
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
