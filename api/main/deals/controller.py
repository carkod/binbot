from flask import Flask, request, current_app as app
from passlib.hash import pbkdf2_sha256
from jose import jwt
from main import tools
from main import auth
import json
from time import time, sleep
import hashlib
import hmac
import math
import sys
from urllib.parse import urlparse
import requests
import pandas as pd
from main.tools import EnumDefinitions, handle_error, Book_Order
from main.account import Account, Balances
from dotenv import load_dotenv
import os
from main.orders.controller import Buy_Order, Sell_Order
from main.tools.round_numbers import round_numbers, round_numbers_ceiling, floatify, stringify_float
from decimal import Decimal
from main.tools.rate_limits import order_rate_limit

load_dotenv()


class Deal:

    @classmethod
    def check_funds(self, bot):
        balances = Balances()
        asset = 0
        funds = 0
        if bot["strategy"] == "long":
            asset = balances.get_quote_asset(bot["pair"])
            funds = balances.get_quote_balance(bot["pair"])
        else:
            asset = balances.get_base_asset(bot["pair"])
            funds = balances.get_base_balance(bot["pair"])

        if float(funds) == 0.0:
            msg = "[BINBOT] Not enough {} to buy {}".format(asset, bot["pair"])
            object =  {"code": -1103, "message": msg}
            return object
        return funds

    def __init__(self, bot):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.base_url = os.getenv("BASE")
        self.binbot_base_url = f'http://{os.getenv("FLASK_DOMAIN")}:{os.getenv("FLASK_PORT")}/api/v1/'
        self.order_url = os.getenv("ORDER")
        self.order_book_url = os.getenv("ORDER_BOOK")
        # Buy order
        self.active_bot = bot
        self.side = EnumDefinitions.order_side[0]
        self.strategy = self.active_bot["strategy"]
        self.symbol = self.active_bot["pair"]
        self.botname = self.active_bot["name"]
        self.active = self.active_bot["active"]
        self.base_order_type = self.active_bot["base_order_type"]
        self.max_so_count = int(self.active_bot["max_so_count"])
        self.price_deviation_so = self.active_bot["price_deviation_so"]
        self.take_profit = self.active_bot["take_profit"]
        self.trailling = self.active_bot["trailling"]
        self.trailling_deviation = self.active_bot["trailling_deviation"]

        
    def handle_fourofour(self, order):
        if "code" not in order:
            # save base deal
            return order
        else:
            print(f"[BINBOT] {order}")
            exit(1)

    
    def initial_computations(self):
        # 2 = base order + take profit
        # 1.0075 = default commission rate
        get_available_funds = self.check_funds(self.active_bot)
        if isinstance(get_available_funds, dict):
            return get_available_funds

        self.balance_usage_size = str(float(self.active_bot["balance_usage"]) * get_available_funds)
        self.division = (float(self.balance_usage_size) / (self.max_so_count + 1)) * 1.0075
        return

    def long_base_order(self):
        url = self.binbot_base_url + os.getenv("BINBOT_BUY")
        pair = self.active_bot["pair"]
        qty = round_numbers(self.division)
        price = float(Book_Order(pair).matching_engine(0, "ask", qty))
        buy_qty = str(round_numbers(qty / price, 0))
        self.long_base_order_price = price

        order = {"pair": pair, "qty": buy_qty, "price": floatify(price)}
        res = requests.post(url=url, data=json.dumps(order))
        handle_error(res)
        base_order = res.json()
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
        index = 0
        for index in range(length):
            index += 1

            # Recursive order
            url = self.binbot_base_url + os.getenv("BINBOT_BUY")
            pair = self.active_bot["pair"]
            qty = math.floor(float(self.division) * 1000000) / 1000000

            # SO mark based on take profit
            increase_from_tp = float(self.take_profit) / int(self.max_so_count)

            # last book order price
            market_price = float(Book_Order(pair).ticker_price())

            # final order price.
            # Index incrementally increases price added markup
            # +1 to exclude index 0 and first base order (index 1) from safety order
            price = market_price * (1 + (increase_from_tp * (index + 1)))
            # round down number
            buy_qty = str(int(qty / price))
            buy_price = str(round_numbers(price, 5))
            data = {"pair": pair, "qty": buy_qty, "price": buy_price}

            # Check rate limits before making order
            check_limits = order_rate_limit(pair, buy_price, buy_qty)
            if isinstance(check_limits, dict):
                return check_limits

            res = requests.post(url=url, data=json.dumps(data))
            handle_error(res)
            order = res.json()
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
                "so_count": index,
            }

            so_deals.append(safety_orders)
            if index > length:
                break
        return so_deals

    def long_take_profit_order(self):
        url = self.binbot_base_url + os.getenv("BINBOT_SELL")
        pair = self.active_bot["pair"]
        qty = round_numbers(self.division)

        market_price = float(Book_Order(pair).matching_engine(0, "bids", qty))
        price = round_numbers(market_price * (1 + float(self.take_profit)), 2)
        order = {"pair": pair, "qty": qty, "price": price}

        # Check rate limits before making order
        order_rate_limit(pair, pair, qty)

        res = requests.post(url=url, data=json.dumps(order))
        handle_error(res)
        order = res.json()

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
        return base_order

    def short_base_order(self):
        url = self.binbot_base_url + os.getenv("BINBOT_SELL")
        pair = self.active_bot["pair"]
        qty = math.floor(self.division * 1000000) / 1000000
        # bids or asks
        price = float(Book_Order(pair).matching_engine(0, "bids", qty))

        order = {"pair": pair, "qty": qty, "price": price}


        rate_limits(pair, price, qty)

        res = requests.post(url=url, data=json.dumps(order))
        handle_error(res)
        res_order = res.json()

        base_deal = {
            "order_id": res_order["orderId"],
            "deal_type": "base_order",
            "active": True,
            "strategy": "long",  # change accordingly
            "pair": res_order["symbol"],
            "order_side": res_order["side"],
            "order_type": res_order["type"],
            "price": res_order["price"],
            "qty": res_order["origQty"],
            "fills": res_order["fills"],
            "time_in_force": res_order["timeInForce"],
        }
        self.base_order_price = res_order["price"]
        return base_deal

    def short_safety_order_generator(self, index):
        length = self.max_so_count
        so_deals = []
        while index < length:
            index += 1
            url = self.binbot_base_url + os.getenv("BINBOT_BUY")
            pair = self.active_bot["pair"]
            qty = math.floor(self.division * 1000000) / 1000000
            price = float(Book_Order(pair).ticker_price())

            order = {"pair": pair, "qty": qty, "price": price}
            res = requests.post(url=url, data=json.dumps(order))
            handle_error(res)
            order = res.json()
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
                "so_count": index,
            }

            so_deals.append(safety_orders)
        return so_deals

    def short_take_profit_order(self):
        url = self.binbot_base_url + os.getenv("BINBOT_BUY")
        pair = self.active_bot["pair"]
        qty = round_numbers(self.division)

        market_price = float(Book_Order(pair).matching_engine(0, "bids", qty))
        price = round_numbers(market_price * (1 + float(self.take_profit)), 2)

        order = {"pair": pair, "qty": qty, "price": price}
        res = requests.post(url=url, data=json.dumps(order))
        handle_error(res)
        order = res.json()
        tp_order = {
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
        return tp_order

    def open_deal(self):
        balance = self.initial_computations()
        if isinstance(balance, dict):
            return balance
        new_deal = {"base_order": {}, "take_profit_order": {}, "so_orders": []}
        deal_strategy = self.strategy
        if deal_strategy == "long":
            # long_base_order = self.long_base_order()
            # if not long_base_order:
            #     print("[BINBOT] Deal: Base order failed")
            # new_deal["base_order"] = long_base_order
            long_safety_order_generator = self.long_safety_order_generator()
            if isinstance(long_safety_order_generator, dict):
                # Returned error code to interface
                return long_safety_order_generator
            if not long_safety_order_generator:
                print("[BINBOT] Deal: Safety orders failed")
            new_deal["so_orders"] = long_safety_order_generator

            long_take_profit_order = self.long_take_profit_order()
            if not long_take_profit_order:
                print("[BINBOT] Deal: Take profit order failed")

            new_deal["take_profit_order"] = long_take_profit_order

        if deal_strategy == "short":
            short_base_order = self.short_base_order()
            if not short_base_order:
                print("[BINBOT] Deal: Base order failed")
            new_deal["base_order"] = short_base_order

            short_safety_order_generator = self.short_safety_order_generator(0)
            if not short_safety_order_generator:
                print("[BINBOT] Deal: Safety orders failed")
            new_deal["so_orders"] = short_safety_order_generator

            short_take_profit_order = self.short_take_profit_order()
            if not short_take_profit_order:
                print("[BINBOT] Deal: Take profit order failed")

            new_deal["take_profit_order"] = short_take_profit_order

        dealId = app.db.deals.save(new_deal)
        dealId = str(dealId)
        return dealId
