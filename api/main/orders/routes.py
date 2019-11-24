from flask import Flask, Blueprint, request, current_app as app
from main.auth import token_required
from main.orders.models import Buy_Order, Sell_Order
from flask_cors import CORS, cross_origin


# initialization
# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy   dog'
# app.config['CORS_HEADERS'] = 'Content-Type'

# cors = CORS(app, resources={r"/user": {"origins": "http://localhost:5000"}})

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

# @order_blueprint.route("/", methods=["PUT"])
# def edit():
# 	return order().edit()

# @order_blueprint.route("/<id>", methods=["DELETE"])
# def delete(id):
# 	return order().delete(id)
