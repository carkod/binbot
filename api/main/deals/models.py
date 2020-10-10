import json
import math
import os
import requests
from flask import current_app as app
from main.orders.models import Buy_Order, Sell_Order
from main.tools import Book_Order, EnumDefinitions, handle_error
from main.tools.round_numbers import round_numbers


class Deal:
    MIN_QTY = os.getenv("MIN_QTY")
    MIN_PRICE = os.getenv("MIN_PRICE")
    MIN_NOTIONAL = os.getenv("MIN_NOTIONAL")
    key = os.getenv("BINANCE_KEY")
    secret = os.getenv("BINANCE_SECRET")
    base_url = os.getenv("BASE")
    order_url = os.getenv("ORDER")
    order_book_url = os.getenv("ORDER_BOOK")
    bb_base_url = os.getenv("FLASK_DOMAIN") + os.getenv("FLASK_PORT")
    bb_buy_order_url = f'{bb_base_url}/order/buy'
    bb_sell_order_url = f'{bb_base_url}/order/sell'

    def __init__(self, bot, app):
        self.active_bot = bot
        self.app = app
        self.default_deal = {
            "order_id": "",
            "deal_type": "base_order",
            "active": "true",
            "strategy": "long",  # change accordingly
            "pair": "",
            "order_side": "BUY",
            "order_type": "LIMIT",
            "price": "0",
            "qty": "0",
            "fills": "0",
            "time_in_force": "GTC",
        }
        self.division = bot["balance_usage_size"] / (int(bot["max_so_count"]) + 2)

        # self.side = EnumDefinitions.order_side[0]
        # self.strategy = bot["strategy"]
        # self.symbol = bot["pair"]
        # self.botname = bot["name"]
        # self.active = bot["active"]
        # self.balance = bot["balance_usage_size"]
        # self.base_order_type = bot["base_order_type"]
        # self.max_so_count = int(bot["max_so_count"])
        # self.price_deviation_so = bot["price_deviation_so"]
        # self.take_profit = bot["take_profit"]
        # self.trailling = bot["trailling"]
        # self.trailling_deviation = bot["trailling_deviation"]

    @staticmethod
    def handle_fourofour(order):
        if "code" not in order:
            # save base deal
            return order
        else:
            print(order)
            exit(1)

    def long_base_order(self):
        pair = self.active_bot['pair']
        qty = round_numbers(self.division)
        price = float(Book_Order(pair).matching_engine(0, 'bids', qty))
        self.long_base_order_price = price
        
        order = {
            "pair": pair,
            "qty": qty,
            "price": price,
        }
        res = requests.post(url=self.bb_buy_order_url, data=json.dumps(order))
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
            pair = self.active_bot['pair']
            qty = math.floor(self.division * 1000000) / 1000000

            # SO mark based on take profit
            increase_from_tp = float(self.take_profit) / int(self.max_so_count)

            # last book order price
            market_price = float(Book_Order(pair).matching_engine(0, 'bids', qty))

            # final order price.
            # Index incrementally increases price added markup
            # +1 to exclude index 0 and first base order (index 1) from safety order
            price = market_price * (1 + (increase_from_tp * (index + 1)))
            # round down number
            price = round_numbers(price, 2)
            order = {
                "pair": pair,
                "qty": qty,
                "price": price,
            }
            res = requests.post(url=self.bb_buy_order_url, data=json.dumps(order))
            handle_error(res)
            order = res.json()
            if self.binance_bug_workaround(order):
                self.long_safety_order_generator()

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
            if index > length:
                break
        return so_deals

    def long_take_profit_order(self):
        pair = self.active_bot['pair']
        qty = round_numbers(self.division)

        market_price = float(Book_Order(pair).matching_engine(0, 'bids', qty))
        price = round_numbers(market_price * (1 + float(self.take_profit)), 2)

        order = {
            "pair": pair,
            "qty": qty,
            "price": price,
        }
        res = requests.post(url=self.bb_sell_order_url, data=json.dumps(order))
        handle_error(res)
        order = res.json()

        if self.binance_bug_workaround(order):
            self.long_take_profit_order()

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
        pair = self.active_bot['pair']
        qty = math.floor(float(self.division) * 1000000) / 1000000
        if qty <= self.MIN_QTY:
            return "[Base order error] Quantity too low"
        price = float(Book_Order(pair).matching_engine(0, 'asks', qty))
        if price <= self.MIN_PRICE:
            return "[Base order error] Price too low"
        if (float(qty) * float(price)) <= self.MIN_NOTIONAL:
            return "[Base order error] Price x Quantity too low"

        order = {
            "pair": pair,
            "qty": qty,
            "price": price,
        }
        res = requests.post(url=self.bb_buy_order_url, data=json.dumps(order))
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
            pair = self.active_bot['pair']
            qty = math.floor(self.division * 1000000) / 1000000
            price = float(Book_Order(pair).matching_engine(0, 'asks', qty))

            order = {
                "pair": pair,
                "qty": qty,
                "price": price,
            }
            res = requests.post(url=self.bb_buy_order_url, data=json.dumps(order))
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
                "so_count": index
            }

            so_deals.append(safety_orders)
        return so_deals

    def short_take_profit_order(self):
        pair = self.active_bot['pair']
        qty = round_numbers(self.division)

        market_price = float(Book_Order(pair).matching_engine(0, 'bids', qty))
        price = round_numbers(market_price * (1 + float(self.take_profit)), 2)
        
        order = {
            "pair": pair,
            "qty": qty,
            "price": price,
        }
        res = requests.post(url=self.bb_buy_order_url, data=json.dumps(order))
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
        new_deal = {"base_order": {}, "take_profit_order": {}, "so_orders": []}
        deal_strategy = self.active_bot["strategy"]
        if deal_strategy == "long":
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

        if deal_strategy == "short":
            short_base_order = self.short_base_order()
            if not short_base_order:
                print("Deal: Base order failed")
            new_deal["base_order"] = short_base_order

            short_safety_order_generator = self.short_safety_order_generator(0)
            if not short_safety_order_generator:
                print("Deal: Safety orders failed")
            new_deal["so_orders"] = short_safety_order_generator

            short_take_profit_order = self.short_take_profit_order()
            if not short_take_profit_order:
                print("Deal: Take profit order failed")

            new_deal["take_profit_order"] = short_take_profit_order 

        dealId = app.db.deals.save(new_deal)
        dealId = str(dealId)
        return dealId
