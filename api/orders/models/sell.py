import hashlib
import hmac
import json
import os
import time as tm
from urllib.parse import urlparse

import requests
from flask import request
from api.tools.handle_error import handle_error
from api.tools.enum_definitions import EnumDefinitions


class Sell_Order:
    """Post order

    Returns:
        [type] -- [description]
    """

    recvWindow = os.getenv("RECV_WINDOW")
    min_funds = os.getenv("MIN_QTY")
    key = os.getenv("BINANCE_KEY")
    secret = os.getenv("BINANCE_SECRET")
    order_url = os.getenv("ORDER")
    order_book_url = os.getenv("ORDER_BOOK")

    def __init__(self):

        # Buy order
        self.side = EnumDefinitions.order_side[1]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

    def post_order_limit(self):
        """
        Returns successful order
        Returns validation failed order (MIN_NOTIONAL, LOT_SIZE etc..)
        """
        data = json.loads(request.data)
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
        headers = {"X-MBX-APIKEY": self.key}

        # Prepare request for signing
        r = requests.Request("POST", url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(
            self.secret.encode("utf-8"), total_params.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        params.append(("signature", signature))

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data

    def post_take_profit_limit(self):
        """
        Returns successful order
        Returns validation failed order (MIN_NOTIONAL, LOT_SIZE etc..)
        """
        data = json.loads(request.data)
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
            ("symbol", symbol),
            ("timestamp", timestamp),
            ("recvWindow", self.recvWindow),
            ("side", self.side),
            ("type", order_type),
            ("price", price),
            ("stopPrice", stop_price),
            ("quantity", qty),
            ("timeInForce", self.timeInForce),
            ("newOrderRespType", "FULL"),
        ]
        headers = {"X-MBX-APIKEY": self.key}

        # Prepare request for signing
        r = requests.Request("POST", url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(
            self.secret.encode("utf-8"), total_params.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        params.append(("signature", signature))

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data

    def post_stop_loss_limit(self):
        """
        Returns successful order
        Returns validation failed order (MIN_NOTIONAL, LOT_SIZE etc..)
        """
        data = json.loads(request.data)
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
            ("symbol", symbol),
            ("timestamp", timestamp),
            ("recvWindow", self.recvWindow),
            ("side", self.side),
            ("type", order_type),
            ("price", price),
            ("stopPrice", stop_price),
            ("quantity", qty),
            ("timeInForce", self.timeInForce),
            ("newOrderRespType", "FULL"),
        ]
        headers = {"X-MBX-APIKEY": self.key}

        # Prepare request for signing
        r = requests.Request("POST", url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(
            self.secret.encode("utf-8"), total_params.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        params.append(("signature", signature))

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data
