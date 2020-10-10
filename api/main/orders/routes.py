from flask import Blueprint
from main.orders.models.orders import Orders
from main.orders.models.book_order import Book_Order
from main.orders.models.buy import Buy_Order
from main.orders.models.sell import Sell_Order

order_blueprint = Blueprint("order", __name__)

@order_blueprint.route("/", methods=["GET"])
def get():
    # Get all orders from Binance? Might be too expensive
        # return Buy_Order(symbol, quantity, type, price).get_balances()
    pass

# @order_blueprint.route("/<id>", methods=["GET"])
# def get_one(id):
#   # Get single order (id = orderId) from Binance
# 	return order().get_one()


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


# @order_blueprint.route("/", methods=["PUT"])
# def edit():
# 	return order().edit()

# @order_blueprint.route("/<id>", methods=["DELETE"])
# def delete(id):
# 	return order().delete(id)
