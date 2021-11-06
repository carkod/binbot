from api.orders.models.buy import BuyOrder
from api.orders.models.orders import Orders
from api.orders.models.sell import SellOrder
from flask import Blueprint
from api.auth import auth

order_blueprint = Blueprint("order", __name__)


@order_blueprint.route("/buy", methods=["POST"])
@auth.login_required
def create_buy_order():
    return BuyOrder().post_order_limit()


@order_blueprint.route("/buy/market", methods=["POST"])
@auth.login_required
def buy_order_market():
    return BuyOrder().post_order_market()


@order_blueprint.route("/buy/take-profit", methods=["POST"])
@auth.login_required
def create_take_profit_buy_order():
    return BuyOrder().post_take_profit_limit()


@order_blueprint.route("/sell", methods=["POST"])
@auth.login_required
def create_sell_order():
    return SellOrder().post_order_limit()


@order_blueprint.route("/sell/take-profit", methods=["POST"])
@auth.login_required
def create_take_profit_sell_order():
    return SellOrder().post_take_profit_limit()


@order_blueprint.route("/buy/stop-limit", methods=["POST"])
@auth.login_required
def create_stop_loss_buy_order():
    return BuyOrder().post_stop_loss_limit()


@order_blueprint.route("/sell/stop-limit", methods=["POST"])
@auth.login_required
def create_stop_loss_sell_order():
    return SellOrder().post_stop_loss_limit()


@order_blueprint.route("/poll", methods=["GET"])
@auth.login_required
def poll_historical_orders():
    return Orders().poll_historical_orders()


@order_blueprint.route("/all", methods=["GET"])
@auth.login_required
def get_all_orders():
    return Orders().get_all_orders()


@order_blueprint.route("/open", methods=["GET"])
@auth.login_required
def get_open_orders():
    return Orders().get_open_orders()


@order_blueprint.route("/close/<symbol>/<orderid>", methods=["DELETE"])
@auth.login_required
def delete_order(symbol, orderid):
    return Orders().delete_order()
