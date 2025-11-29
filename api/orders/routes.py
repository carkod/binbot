from fastapi import APIRouter
from tools.exceptions import BinanceErrors
from tools.handle_error import json_response, json_response_error
from orders.controller import OrderFactory
from orders.schemas import OrderParams
from exchange_apis.binance.orders import BinanceOrderController
from exchange_apis.binance.base import BinanceApi

order_blueprint = APIRouter()


@order_blueprint.post("/buy", tags=["orders"])
def create_buy_order(item: OrderParams):
    order = OrderFactory().get_order_controller()
    return order.buy_order(symbol=item.pair, qty=item.qty)


@order_blueprint.post("/sell", tags=["orders"])
def create_sell_order(item: OrderParams):
    order = OrderFactory().get_order_controller()
    return order.sell_order(symbol=item.pair, qty=item.qty)


@order_blueprint.delete("/close/{symbol}/{orderid}", tags=["orders"])
def delete_order(symbol, orderid):
    try:
        data = BinanceApi().delete_order(symbol, orderid)
        resp = json_response({"message": "Order deleted!", "data": data})
    except BinanceErrors as error:
        resp = json_response_error(error.message)
        pass

    return resp


@order_blueprint.get("/margin/sell/{symbol}/{qty}", tags=["orders"])
def margin_sell(symbol, qty):
    try:
        data = BinanceOrderController().sell_margin_order(symbol, qty)
        return json_response({"message": "Margin Sell order placed", "data": data})
    except BinanceErrors as error:
        return json_response_error(error.message)
