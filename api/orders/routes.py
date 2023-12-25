from fastapi import APIRouter
from orders.controller import OrderController
from orders.schemas import OrderRequest, OrderParams


order_blueprint = APIRouter()


@order_blueprint.post("/buy", tags=["orders"])
def create_buy_order(item: OrderParams):
    return OrderController(symbol=item.pair).buy_order(item)



@order_blueprint.post("/sell", tags=["orders"])
def create_sell_order(item: OrderParams):
    return OrderController(symbol=item.pair).sell_order(item)


@order_blueprint.get("/open", tags=["orders"])
def get_open_orders():
    # Symbol not required
    return OrderController(symbol=None).get_open_orders()


@order_blueprint.delete("/close/{symbol}/{orderid}", tags=["orders"])
def delete_order(symbol, orderid):
    return OrderController(symbol=symbol).delete_order(symbol, orderid)


@order_blueprint.get("/margin/sell/{symbol}/{qty}", tags=["orders"])
def margin_sell(symbol, qty):
    return OrderController(symbol=symbol).sell_margin_order(symbol, qty)
