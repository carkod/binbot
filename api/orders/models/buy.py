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
        data = request.json
        symbol = data["pair"]
        qty = data["qty"]
        price = data["price"]

        # Limit order
        order_type = EnumDefinitions.order_types[0]
        timestamp = int(round(tm.time() * 1000))
        url = self.order_url

        # Get data for a single crypto e.g. BTT in BNB market
        params = [
            ("recvWindow", self.recvWindow),
            ("timestamp", timestamp),
            ("symbol", symbol),
            ("side", self.side),
            ("type", order_type),
            ("timeInForce", self.timeInForce),
            ("price", price),
            ("quantity", qty),
        ]
        data = self._user_data_request(url=self.order_url, method="POST", params=params)
        return data

    def post_order_market(self):
        data = request.json
        symbol = data["pair"]
        qty = data["qty"]

        # Limit order
        order_type = EnumDefinitions.order_types[1]
        timestamp = int(round(tm.time() * 1000))
        url = self.order_url

        # Get data for a single crypto e.g. BTT in BNB market
        params = [
            ("recvWindow", self.recvWindow),
            ("timestamp", timestamp),
            ("symbol", symbol),
            ("side", self.side),
            ("type", order_type),
            ("timeInForce", self.timeInForce),
            ("quantity", qty),
        ]
        data = self._user_data_request(url=self.order_url, method="POST", params=params)
        return data

    def post_take_profit_limit(self):
        data = request.json
        symbol = data["pair"]
        qty = data["qty"]
        price = data["price"]
        stop_price = data["stop_price"] if "stop_price" in data else price

        # Limit order
        order_type = EnumDefinitions.order_types[5]
        timestamp = int(round(tm.time() * 1000))
        url = self.order_url

        # Get data for a single crypto e.g. BTT in BNB market
        params = [
            ("recvWindow", self.recvWindow),
            ("timestamp", timestamp),
            ("symbol", symbol),
            ("side", self.side),
            ("type", order_type),
            ("timeInForce", self.timeInForce),
            ("price", price),
            ("stopPrice", stop_price),
            ("quantity", qty),
        ]
        data = self._user_data_request(url=self.order_url, method="POST", params=params)
        return data

    def post_stop_loss_limit(self):
        data = request.json
        symbol = data["pair"]
        qty = data["qty"]
        price = data["price"]
        stop_price = data["stop_price"] if "stop_price" in data else price

        # Limit order
        order_type = EnumDefinitions.order_types[3]
        timestamp = int(round(tm.time() * 1000))
        url = self.order_url

        # Get data for a single crypto e.g. BTT in BNB market
        params = [
            ("recvWindow", self.recvWindow),
            ("timestamp", timestamp),
            ("symbol", symbol),
            ("side", self.side),
            ("type", order_type),
            ("timeInForce", self.timeInForce),
            ("price", price),
            ("stopPrice", stop_price),
            ("quantity", qty),
            ("newOrderRespType", "FULL"),
        ]
        data = self._user_data_request(url=self.order_url, method="POST", params=params)
        return data
