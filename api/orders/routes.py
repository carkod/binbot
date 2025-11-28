from fastapi import APIRouter
from tools.exceptions import BinanceErrors
from tools.handle_error import json_response, json_response_error
from orders.controller import OrderFactory
from orders.schemas import OrderParams


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
        order = OrderFactory().get_order_controller()
        data = order.delete_order(symbol, orderid)
        resp = json_response({"message": "Order deleted!", "data": data})
    except BinanceErrors as error:
        resp = json_response_error(error.message)
        pass

    return resp


@order_blueprint.get("/margin/sell/{symbol}/{qty}", tags=["orders"])
def margin_sell(symbol, qty):
    order = OrderFactory().get_order_controller()
    return order.sell_margin_order(symbol, qty)


@order_blueprint.get("/all-orders", tags=["orders"])
def get_all_orders(symbol, order_id=0, start_time=None):
    try:
        order = OrderFactory().get_order_controller()
        data = order.get_all_orders(symbol, order_id=order_id, start_time=start_time)
        return json_response({"message": "Orders found!", "data": data})
    except ValueError as error:
        return json_response_error(error.args[0])
    except BinanceErrors as error:
        return json_response_error(error.message)
