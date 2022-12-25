from fastapi import APIRouter
from orders.controller import OrderController
from orders.schemas import OrderRequest, OrderParams


order_blueprint = APIRouter()


@order_blueprint.post("/buy", tags=["orders"])
def create_buy_order(item: OrderParams):
    return OrderController().buy_order(item)



@order_blueprint.post("/sell", tags=["orders"])
def create_sell_order(item: OrderParams):
    return OrderController().sell_order(item)


@order_blueprint.get("/all", tags=["orders"])
def get_all_orders():
    return OrderController().get_all_orders()


@order_blueprint.get("/open", tags=["orders"])
def get_open_orders():
    return OrderController().get_open_orders()


@order_blueprint.delete("/close/{symbol}/{orderid}", tags=["orders"])
def delete_order(symbol, orderid):
    return OrderController().delete_order(symbol, orderid)
