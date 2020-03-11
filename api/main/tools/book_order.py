import os
import requests
from main.tools import handle_error, EnumDefinitions
import pandas as pd


class Book_Order:
    def __init__(self, symbol):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.base_url = os.getenv("BASE")
        self.order_url = os.getenv("ORDER")
        self.order_book_url = os.getenv("ORDER_BOOK")
        self.price = os.getenv("TICKER_PRICE")
        self.avg_price = os.getenv("AVERAGE_PRICE")
        self.symbol = symbol

    """
    Simpler matching engine, no need for quantity
    """

    def last_price(self, order_side="bids"):
        url = self.base_url + self.order_book_url
        limit = EnumDefinitions.order_book_limits[0]
        params = [("symbol", self.symbol), ("limit", limit)]
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        if order_side == "bids":
            df = pd.DataFrame(data["bids"], columns=["price", "qty"])
        elif order_side == "asks":
            df = pd.DataFrame(data["asks"], columns=["price", "qty"])

        else:
            print("Incorrect bid/ask keyword for matching_engine")
            exit(1)

        price = df["price"].astype(float)[0]
        return price

    """
    Buy order = bids
    Sell order = ask
    """

    def matching_engine(self, limit_index=0, order_side="bids", qty=0):
        url = self.base_url + self.order_book_url
        limit = EnumDefinitions.order_book_limits[limit_index]
        params = [("symbol", self.symbol), ("limit", limit)]
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        if order_side == "bids":
            df = pd.DataFrame(data["bids"], columns=["price", "qty"])
        elif order_side == "ask":
            df = pd.DataFrame(data["asks"], columns=["price", "qty"])

        else:
            print("Incorrect bid/ask keyword for matching_engine")
            exit(1)

        df["qty"] = df["qty"].astype(float)

        # If quantity matches list
        match_qty = df[df["qty"] > float(qty)]
        condition = df["qty"] > float(qty)
        if condition.any() == False:
            limit += limit
            self.matching_engine(limit)
        return match_qty["price"][0]

    def ticker_price(self):
        url = self.base_url + self.price
        params = [("symbol", self.symbol)]
        res = requests.get(url=url, params=params)
        handle_error(res)
        price = res.json()["price"]
        return price
