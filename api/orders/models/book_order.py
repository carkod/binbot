import os
import requests
from api.tools.handle_error import handle_error
from api.tools.enum_definitions import EnumDefinitions
import pandas as pd
from api.tools.round_numbers import round_numbers


class Book_Order:
    def __init__(self, symbol):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.order_url = os.getenv("ORDER")
        self.order_book_url = os.getenv("ORDER_BOOK")
        self.price = os.getenv("TICKER_PRICE")
        self.avg_price = os.getenv("AVERAGE_PRICE")
        self.symbol = symbol

    """
    Simpler matching engine, no need for quantity
    """

    def last_price(self, order_side="bids"):
        url = self.order_book_url
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

    def matching_engine(self, order_side, qty, limit_index=0):
        """
        Match quantity with available 100% fill order price,
        so that order can immediately buy/sell
        @param: order_side -
            Buy order = get ask prices = True
            Sell order = get bids prices = False
        @param: qty - quantity wanted to be bought
        @param: order_side - BUY or SELL
        """

        url = self.order_book_url
        limit = EnumDefinitions.order_book_limits[limit_index]
        params = [("symbol", self.symbol), ("limit", limit)]
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        if order_side:
            df = pd.DataFrame(data["bids"], columns=["price", "qty"])
        else:
            df = pd.DataFrame(data["asks"], columns=["price", "qty"])

        df["qty"] = df["qty"].astype(float)

        # If quantity matches list
        match_qty = df[df.qty > float(qty)]
        condition = df["qty"] > float(qty)
        if not condition.any():
            limit_index += limit_index
            if limit_index == 4:
                return None
            self.matching_engine(order_side, qty, limit_index)
        final_qty = match_qty["price"].iloc[0]
        return final_qty

    def ticker_price(self):
        url = self.price
        params = [("symbol", self.symbol)]
        res = requests.get(url=url, params=params)
        handle_error(res)
        price = res.json()["price"]
        return price
