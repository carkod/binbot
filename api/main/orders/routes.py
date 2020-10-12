from flask import Blueprint
from main.orders.models.orders import Orders
from main.orders.models.book_order import Book_Order
from main.orders.models.buy import Buy_Order
from main.orders.models.sell import Sell_Order
from main.orders.models.order_sockets import OrderUpdates

order_blueprint = Blueprint("order", __name__)

@order_blueprint.route("/buy", methods=["POST"])
def create_buy_order():
    return Buy_Order().post_order_limit()

@order_blueprint.route("/buy/market", methods=["POST"])
def buy_order_market():
    return Buy_Order().post_order_limit()

@order_blueprint.route("/sell", methods=["POST"])
def create_sell_order():
    return Sell_Order().post_order_limit()

@order_blueprint.route("/open", methods=["GET"])
def get_open_orders():
    return Orders().get_open_orders()

@order_blueprint.route("/", methods=["DELETE"])
def delete_order():
    return Orders().delete_order()

@order_blueprint.route("/order-updates", methods=["GET"])
def orders_update():
    updates = OrderUpdates()
    listen_key = updates.get_listenkey()["listenKey"]
    stream = updates.open_stream()
    if stream:
        result = updates.get_stream(listen_key)
        print(result)

    # Comment out after development is finished
    updates.close_stream()
    return result
