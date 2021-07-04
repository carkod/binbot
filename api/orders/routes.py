from api.orders.models.buy import Buy_Order
from api.orders.models.orders import Orders
from api.orders.models.sell import Sell_Order
from flask import Blueprint

order_blueprint = Blueprint("order", __name__)


@order_blueprint.route("/buy", methods=["POST"])
def create_buy_order():
    return Buy_Order().post_order_limit()


@order_blueprint.route("/buy/market", methods=["POST"])
def buy_order_market():
    return Buy_Order().post_order_market()


@order_blueprint.route("/buy/take-profit", methods=["POST"])
def create_take_profit_buy_order():
    return Buy_Order().post_take_profit_limit()


@order_blueprint.route("/sell", methods=["POST"])
def create_sell_order():
    return Sell_Order().post_order_limit()


@order_blueprint.route("/sell/take-profit", methods=["POST"])
def create_take_profit_sell_order():
    return Sell_Order().post_take_profit_limit()


@order_blueprint.route("/buy/stop-limit", methods=["POST"])
def create_stop_loss_buy_order():
    return Buy_Order().post_stop_loss_limit()


@order_blueprint.route("/sell/stop-limit", methods=["POST"])
def create_stop_loss_sell_order():
    return Sell_Order().post_stop_loss_limit()


@order_blueprint.route("/poll", methods=["GET"])
def poll_historical_orders():
    return Orders().poll_historical_orders()


@order_blueprint.route("/all", methods=["GET"])
def get_all_orders():
    return Orders().get_all_orders()


@order_blueprint.route("/open", methods=["GET"])
def get_open_orders():
    return Orders().get_open_orders()


@order_blueprint.route("/close/<symbol>/<orderid>", methods=["DELETE"])
def delete_order(symbol, orderid):
    return Orders().delete_order()
