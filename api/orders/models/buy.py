import hashlib
import hmac
import time as tm
from urllib.parse import urlparse

import requests
from api.apis import BinanceApi
from api.tools.enum_definitions import EnumDefinitions
from api.tools.handle_error import handle_error
from flask import request


class BuyOrder(BinanceApi):
    """
    Binance Post order
    """

    def __init__(self):

        # Buy order
        self.side = EnumDefinitions.order_side[0]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

    def post_order_limit(self):
        symbol = request.json.get("pair")
        qty = request.json.get("qty")
        price = request.json.get("price")

        # Limit order
        order_type = EnumDefinitions.order_types[0]

        # Get data for a single crypto e.g. BTT in BNB market
        payload = {
            "symbol": symbol,
            "side": self.side,
            "type": order_type,
            "timeInForce": self.timeInForce,
            "price": price,
            "quantity": qty,
        }
        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        return data

    def post_order_market(self):
        symbol = request.json.get("pair")
        qty = request.json.get("qty")

        # Limit order
        order_type = EnumDefinitions.order_types[1]

        # Get data for a single crypto e.g. BTT in BNB market
        payload = {
            "symbol": symbol,
            "side": self.side,
            "type": order_type,
            "timeInForce": self.timeInForce,
            "quantity": qty,
        }
        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        return data

    def post_take_profit_limit(self):
        symbol = request.json.get("pair")
        qty = request.json.get("qty")
        price = request.json.get("price")
        stop_price = request.json.get("stop_price") if request.json.get("stop_price") else price

        # Limit order
        order_type = EnumDefinitions.order_types[5]

        # Get data for a single crypto e.g. BTT in BNB market
        payload = {
            "symbol": symbol,
            "side": self.side,
            "type": order_type,
            "timeInForce": self.timeInForce,
            "price": price,
            "stopPrice": stop_price,
            "quantity": qty,
        }
        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        return data

    def post_stop_loss_limit(self):
        symbol = request.json.get("pair")
        qty = request.json.get("qty")
        price = request.json.get("price")
        stop_price = request.json.get("stop_price") if request.json.get("stop_price") else price

        # Limit order
        order_type = EnumDefinitions.order_types[3]

        # Get data for a single crypto e.g. BTT in BNB market
        payload = {
            "symbol": symbol,
            "side": self.side,
            "type": order_type,
            "timeInForce": self.timeInForce,
            "price": price,
            "stopPrice": stop_price,
            "quantity": qty,
            "newOrderRespType": "FULL",
        }
        data = self.signed_request(url=self.order_url, method="POST", payload=payload)
        return data
