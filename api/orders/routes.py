from orders.models.buy import BuyOrder
from orders.models.orders import Orders
from orders.models.sell import SellOrder
from fastapi import APIRouter

order_blueprint = APIRouter()


@order_blueprint.post("/buy", tags=["orders"])
def create_buy_order():
    return BuyOrder().post_order_limit()


@order_blueprint.post("/buy/market", tags=["orders"])
def buy_order_market():
    return BuyOrder().post_order_market()


@order_blueprint.post("/buy/take-profit", tags=["orders"])
def create_take_profit_buy_order():
    return BuyOrder().post_take_profit_limit()


@order_blueprint.post("/sell", tags=["orders"])
def create_sell_order():
    return SellOrder().post_order_limit()


@order_blueprint.post("/sell/take-profit", tags=["orders"])
def create_take_profit_sell_order():
    return SellOrder().post_take_profit_limit()


@order_blueprint.post("/buy/stop-limit", tags=["orders"])
def create_stop_loss_buy_order():
    return BuyOrder().post_stop_loss_limit()


@order_blueprint.post("/sell/stop-limit", tags=["orders"])
def create_stop_loss_sell_order():
    return SellOrder().post_stop_loss_limit()


@order_blueprint.get("/all", tags=["orders"])
def get_all_orders():
    return Orders().get_all_orders()


@order_blueprint.get("/open", tags=["orders"])
def get_open_orders():
    return Orders().get_open_orders()


@order_blueprint.delete("/close/{symbol}/{orderid}", tags=["orders"])
def delete_order(symbol, orderid):
    return Orders().delete_order(symbol, orderid)
