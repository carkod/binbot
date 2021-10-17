import hashlib
import hmac
import json
import time as tm
from urllib.parse import urlparse

import pandas as pd
import requests
from api.account import Account
from api.apis import BinanceApi
from api.tools import EnumDefinitions, handle_error


class BuyOrder(BinanceApi):
    """Post order

    Returns:
        [type] -- [description]
    """

    def __init__(self, symbol, quantity, order_type, price):

        # Buy order
        self.side = EnumDefinitions.order_side[0]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

        # Bot details
        self.symbol = symbol
        self.quantity = quantity
        self.type = order_type
        self.price = price

    def get_balances(self):
        data = json.loads(Account().get_balances().data)["data"]
        available_balance = 0
        for i in range(len(data)):
            if data[i]["asset"] == "BTC":
                available_balance = data[i]["free"]
                return available_balance
        return available_balance

    def last_order_book_price(self, limit_index, order_side="bids"):
        """
        Buy order = bids
        Sell order = ask
        """
        url = self.order_book_url
        limit = EnumDefinitions.order_book_limits[limit_index]
        params = [
            ("symbol", self.symbol),
            ("limit", limit),
        ]
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        if order_side == "bids":
            df = pd.DataFrame(data["bids"], columns=["price", "qty"])
        elif order_side == "ask":
            df = pd.DataFrame(data["ask"], columns=["price", "qty"])

        else:
            print("Incorrect bid/ask keyword for last_order_book_price")
            exit(1)

        df["qty"] = df["qty"].astype(float)

        # If quantity matches list
        match_qty = df[df["qty"] > float(self.quantity)]
        condition = df["qty"] > float(self.quantity)
        if not condition.any():
            limit += limit
            self.last_order_book_price(limit)

        return match_qty["price"][0]

    def post_order_limit(self, limit_price=None):
        """
        Returns successful order
        Returns validation failed order (MIN_NOTIONAL, LOT_SIZE etc..)
        """
        # Limit order
        order_type = EnumDefinitions.order_types[0]
        timestamp = int(round(tm.time() * 1000))
        if limit_price:
            price = self.last_order_book_price(0) * (1 + limit_price)
        else:
            price = self.last_order_book_price(0)
        qty = round(float(price) / float(self.quantity), 0)
        # Get data for a single crypto e.g. BTT in BNB market
        params = [
            ("recvWindow", self.recvWindow),
            ("timestamp", timestamp),
            ("symbol", self.symbol),
            ("side", self.side),
            ("type", order_type),
            ("timeInForce", self.timeInForce),
            ("price", price),
            ("quantity", qty),
        ]
        data = self._user_data_request(url=self.order_url, method="POST", params=params)
        return data
