from fastapi import APIRouter
from tools.exceptions import BinanceErrors
from tools.handle_error import json_response, json_response_error
from orders.controller import OrderController
from orders.schemas import OrderParams


order_blueprint = APIRouter()


@order_blueprint.post("/buy", tags=["orders"])
def create_buy_order(item: OrderParams):
    return OrderController(symbol=item.pair).buy_order(item)



@order_blueprint.post("/sell", tags=["orders"])
def create_sell_order(item: OrderParams):
    return OrderController(symbol=item.pair).sell_order(item)


@order_blueprint.delete("/close/{symbol}/{orderid}", tags=["orders"])
def delete_order(symbol, orderid):
    try:
        data = OrderController(symbol=symbol).delete_order(symbol, orderid)
        resp = json_response({"message": "Order deleted!", "data": data})
    except BinanceErrors as error:
        resp = json_response_error(error.message)
        pass

    return resp

@order_blueprint.get("/margin/sell/{symbol}/{qty}", tags=["orders"])
def margin_sell(symbol, qty):
    return OrderController(symbol=symbol).sell_margin_order(symbol, qty)

@order_blueprint.get("/all-orders", tags=["orders"])
def get_all_orders(symbol, order_id=0, start_time=None):
    try:
        data = OrderController(symbol=symbol).get_all_orders(symbol, order_id=order_id, start_time=start_time)
        return json_response({"message": "Orders found!", "data": data})
    except ValueError as error:
        return json_response_error(error.args[0])
    except BinanceErrors as error:
        return json_response_error(error.message)
