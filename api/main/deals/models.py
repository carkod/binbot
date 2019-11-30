from flask import Flask, request, current_app as app
from passlib.hash import pbkdf2_sha256
from jose import jwt
from main import tools
from main import auth
import json
import time as tm
import hashlib
import hmac
import math
import sys
import time as tm
from urllib.parse import urlparse
import requests
import pandas as pd
from main.tools import EnumDefinitions, handle_error, Book_Order
from main.account import Account
from dotenv import load_dotenv
import os
from main.orders.models import Buy_Order, Sell_Order

load_dotenv()


class Deal:
    def __init__(self, bot, app):
        self.app = app
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.base_url = os.getenv("BASE")
        self.order_url = os.getenv("ORDER")
        self.order_book_url = os.getenv("ORDER_BOOK")
        # Buy order
        self.side = EnumDefinitions.order_side[0]

        self.symbol = bot["pair"]
        self.botname = bot["name"]
        self.active = bot["active"]
        self.balance = bot["balance_usage_size"]
        self.base_order_type = bot["base_order_type"]
        self.max_so_count = int(bot["max_so_count"])
        self.price_deviation_so = bot["price_deviation_so"]
        self.division = self.balance / self.max_so_count + 2
        self.take_profit = bot["take_profit"]
        self.trailling = bot["trailling"]
        self.trailling_deviation = bot["trailling_deviation"]

    def handle_fourofour(self, order):
        if "code" not in order:
            # save base deal
            return order
        else:
            print(order)
            exit(1)

    def long_base_order(self):
        # base_order = Buy_Order(symbol=self.symbol, quantity=self.division, type=self.base_order_type).post_order_limit()
        base_order = {
            "clientOrderId": "KxwRuUmnQqgcs5y7KWU77t",
            "cummulativeQuoteQty": "0.00000000",
            "executedQty": "0.00000000",
            "fills": [],
            "orderId": 263599681,
            "orderListId": -1,
            "origQty": "4.00000000",
            "price": "0.00039920",
            "side": "BUY",
            "status": "NEW",
            "symbol": "EOSBTC",
            "timeInForce": "GTC",
            "transactTime": 1574040139349,
            "type": "LIMIT",
        }
        base_deal = {
            "order_id": base_order["orderId"],
            "deal_type": "base_order",
            "strategy": "long",  # change accordingly
            "pair": base_order["symbol"],
            "order_side": base_order["side"],
            "order_type": base_order["type"],
            "price": base_order["price"],
            "qty": base_order["origQty"],
            "fills": base_order["fills"],
            "time_in_force": base_order["timeInForce"],
        }
        self.base_order_price = base_order["price"]
        return base_deal

    def long_safety_order_generator(self):
        length = self.max_so_count
        so_deals = []
        for index in range(length):
            index += 1
            price = self.division * index
            # order = Buy_Order(symbol=self.symbol, quantity=self.division, type='LIMIT', price=price).post_order_limit()
            order = {
                "clientOrderId": "KxwRuUmnQqgcs5y7KWU77t",
                "cummulativeQuoteQty": "0.00000000",
                "executedQty": "0.00000000",
                "fills": [],
                "orderId": 263599681,
                "orderListId": -1,
                "origQty": "4.00000000",
                "price": "0.00039920",
                "side": "BUY",
                "status": "NEW",
                "symbol": "EOSBTC",
                "timeInForce": "GTC",
                "transactTime": 1574040139349,
                "type": "LIMIT",
            }
            safety_orders = {
                "order_id": order["orderId"],
                "deal_type": "safety_order",
                "strategy": "long",  # change accordingly
                "pair": order["symbol"],
                "order_side": order["side"],
                "order_type": order["type"],
                "price": price,
                "qty": order["origQty"],
                "fills": order["fills"],
                "time_in_force": order["timeInForce"],
                "so_count": index
            }

            so_deals.append(safety_orders)
        return so_deals

    def long_take_profit_order(self):
        price = self.division * self.max_so_count
        # order = Buy_Order(symbol=self.symbol, quantity=self.division, type='LIMIT', price=price).post_order_limit()
        # Make requests as with normal api
        order = {
            "clientOrderId": "KxwRuUmnQqgcs5y7KWU77t",
            "cummulativeQuoteQty": "0.00000000",
            "executedQty": "0.00000000",
            "fills": [],
            "orderId": 263599681,
            "orderListId": -1,
            "origQty": "4.00000000",
            "price": "0.00039920",
            "side": "BUY",
            "status": "NEW",
            "symbol": "EOSBTC",
            "timeInForce": "GTC",
            "transactTime": 1574040139349,
            "type": "LIMIT",
        }
        base_order = {
            "deal_type": "take_profit",
            "order_id": order["orderId"],
            "strategy": "long",  # change accordingly
            "pair": order["symbol"],
            "order_side": order["side"],
            "order_type": order["type"],
            "price": price,
            "qty": order["origQty"],
            "fills": order["fills"],
            "time_in_force": order["timeInForce"],
        }
        if "code" not in order:
            return base_order
        else:
            print(order)
            exit(1)

    def open_deal(self):
        new_deal = {"base_order": {}, "take_profit_order": {}, "so_orders": []}
        long_base_order = self.long_base_order()
        if not long_base_order:
            print("Deal: Base order failed")
        new_deal["base_order"] = long_base_order

        long_safety_order_generator = self.long_safety_order_generator()
        if not long_safety_order_generator:
            print("Deal: Safety orders failed")
        new_deal["so_orders"] = long_safety_order_generator

        long_take_profit_order = self.long_take_profit_order()
        if not long_take_profit_order:
            print("Deal: Take profit order failed")

        new_deal["take_profit_order"] = long_take_profit_order

        dealId = app.db.deals.save(new_deal)
        dealId = str(dealId)
        return dealId

