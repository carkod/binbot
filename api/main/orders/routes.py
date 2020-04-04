from flask import Flask, Blueprint, request, current_app as app
from main.auth import token_required
from main.orders.controllers import Buy_Order, Sell_Order, Orders, OrderUpdates
from flask_cors import CORS, cross_origin


order_blueprint = Blueprint("order", __name__)


@order_blueprint.route("/", methods=["GET"])
def get():
    # Get all orders from Binance? Might be too expensive
    # return Buy_Order(symbol, quantity, type, price).get_balances()
    pass


@order_blueprint.route("/buy", methods=["POST"])
def create_buy_order():
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
