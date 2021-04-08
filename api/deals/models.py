import json
import math
import os

import requests
from flask import Response, current_app as app
from api.orders.models.book_order import Book_Order, handle_error
from api.tools.round_numbers import round_numbers, supress_notation
from api.tools.jsonresp import jsonResp_message, jsonResp
from api.account.models import Account

class Deal(Account):
    order_book_url = os.getenv("ORDER_BOOK")
    bb_base_url = f'{os.getenv("FLASK_DOMAIN")}:{os.getenv("FLASK_PORT")}'
    bb_buy_order_url = f'{bb_base_url}/order/buy'
    bb_tp_buy_order_url = f'{bb_base_url}/order/buy/take-profit'
    bb_buy_market_order_url = f'{bb_base_url}/order/buy/market'
    bb_sell_order_url = f'{bb_base_url}/order/sell'
    bb_tp_sell_order_url = f'{bb_base_url}/order/sell/take-profit'
    bb_sell_market_order_url = f'{bb_base_url}/order/sell/market'
    bb_opened_orders_url = f'{bb_base_url}/order/open'
    bb_close_order_url = f'{bb_base_url}/order/close'
    bb_stop_buy_order_url = f'{bb_base_url}/order/buy/stop-limit'
    bb_stop_sell_order_url = f'{bb_base_url}/order/sell/stop-limit'

    def __init__(self, bot, app):
        # Inherit also the __init__ from parent class
        super(self.__class__, self).__init__()

        self.active_bot = bot
        self.MIN_PRICE = float(self.price_filter_by_symbol(self.active_bot["pair"], "minPrice"))
        self.MIN_QTY = float(self.lot_size_by_symbol(self.active_bot["pair"], "minQty"))
        self.MIN_NOTIONAL = float(self.min_notional_by_symbol(self.active_bot["pair"]))
        self.app = app
        self.default_deal = {
            "order_id": "",
            "deal_type": "base_order",
            "active": "true",
            "strategy": "long",  # change accordingly
            "pair": "",
            "order_side": "BUY",
            "order_type": "LIMIT",  # always limit orders
            "price": "0",
            "qty": "0",
            "fills": "0",
            "time_in_force": "GTC",
        }
        self.total_amount = 0
        self.max_so_count = int(bot["max_so_count"])
        self.balances = 0
        self.decimal_precision = self.get_quote_asset_precision(self.active_bot["pair"])

    def initialization(self):
        """
        Initial checks to see if the deal is possible
        - Do we have enough balance?
        - If we have enough balance allocate division
        - If long position, check base (left) asset
        - If short position, check quote (right) asset
        """

        asset = self.find_quoteAsset(self.active_bot["pair"])
        self.balance = self.get_one_balance(asset)

        if not self.balance:
            return jsonResp_message(f"[Deal init error] No {asset} balance", 200)

        self.active_bot["balance_usage_size"] = self.get_one_balance(asset)

    def long_base_order(self):
        pair = self.active_bot['pair']
        # Long position does not need qty in take_profit
        # initial price with 1 qty should return first match
        book_order = Book_Order(pair)
        initial_price = float(book_order.matching_engine(False, 1))
        qty = round_numbers((float(self.active_bot["base_order_size"]) / float(initial_price)), 0)
        price = float(book_order.matching_engine(False, qty))
        # price = 0.000186
        self.price = price
        amount = float(qty) / float(price)
        self.total_amount = qty

        if price:
            if price <= float(self.MIN_PRICE):
                return jsonResp_message("[Base order error] Price too low", 200)
        # Avoid common rate limits
        if qty <= float(self.MIN_QTY):
            return jsonResp_message("[Base order error] Quantity too low", 200)
        if amount <= float(self.MIN_NOTIONAL):
            return jsonResp_message("[Base order error] Price x Quantity too low", 200)

        if price:
            order = {
                "pair": pair,
                "qty": qty,
                "price": supress_notation(price),
            }
            res = requests.post(url=self.bb_buy_order_url, json=order)
        else:
            # Matching engine failed - market order
            order = {
                "pair": pair,
                "qty": qty,
            }
            res = requests.post(url=self.bb_buy_market_order_url, json=order)

        if isinstance(handle_error(res), Response):
            return handle_error(res)
        order = res.json()

        base_deal = {
            "order_id": order["orderId"],
            "deal_type": "base_order",
            "strategy": "long",  # change accordingly
            "pair": order["symbol"],
            "order_side": order["side"],
            "order_type": order["type"],
            "price": order["price"],
            "qty": order["origQty"],
            "fills": order["fills"],
            "time_in_force": order["timeInForce"],
            "status": order["status"],
        }
        self.base_order_price = order["price"]
        self.active_bot["deals"].append(base_deal)
        botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": base_deal }})
        if not botId:
            resp = jsonResp(
                {"message": "Failed to save Base order", "botId": str(findId)},
                200,
            )
            return resp

        return base_deal

    def long_safety_order_generator(self):
        length = self.max_so_count
        so_deals = []
        base_order_deal = next((bo_deal for bo_deal in self.active_bot["deals"] if bo_deal["deal_type"] == "base_order"), None)
        take_profit = float(self.active_bot["take_profit"])
        so_deviation = float(self.active_bot["price_deviation_so"]) / 100
        index = 0
        for index in range(length):
            index += 1

            # Recursive order
            pair = self.active_bot['pair']
            so_proportion = self.active_bot["so_size"]
            qty = round_numbers(so_proportion, 8)

            # Stop price
            stop_price = float(base_order_deal["price"])

            order = {
                "pair": pair,
                "qty": qty,
                "price": supress_notation(stop_price),
                "stop_price": supress_notation(stop_price)
            }
            res = requests.post(url=self.bb_stop_buy_order_url, json=order)
            if isinstance(handle_error(res), Response):
                return handle_error(res)

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
                "status": order["status"],
            }

            so_deals.append(safety_orders)
            if index > length:
                break
        
        self.active_bot["deals"].append(so_deals)
        botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": so_deals }})
        if not botId:
            resp = jsonResp(
                {"message": "Failed to save take_profit deal in the bot", "botId": str(findId)},
                200,
            )
            return resp

        return so_deals

    def long_take_profit_order(self):
        """
        Execute long strategy (buy and sell higher)
        take profit order (Binance take_profit)
        - We only have stop_price, because there are no book bids/asks in t0
        - Perform validations so we can avoid hitting endpoint errors
        - take_profit order can ONLY be executed once base order is filled (on Binance)
        """
        pair = self.active_bot['pair']
        price = (1 + (float(self.active_bot["take_profit"]) / 100)) * self.price
        decimal_precision = self.get_quote_asset_precision(pair)
        qty = round_numbers(self.total_amount, 0)
        price = round_numbers(price, 6)

        # Validations
        if price:
            if price <= float(self.MIN_PRICE):
                return jsonResp_message("[Long take profit order error] Price too low", 200)
        # Avoid common rate limits
        if qty <= float(self.MIN_QTY):
            return jsonResp_message("[Long take profit order error] Quantity too low", 200)
        if price * qty <= float(self.MIN_NOTIONAL):
            return jsonResp_message("[Long take profit order error] Price x Quantity too low", 200)

        order = {
            "pair": pair,
            "qty": qty,
            "price": supress_notation(price), # Theoretically stop_price, as we don't have book orders
            "stop_price": supress_notation(price),
        }
        res = requests.post(url=self.bb_sell_order_url, json=order)
        if isinstance(handle_error(res), Response):
            return handle_error(res)
        order = res.json()

        take_profit_order = {
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
            "status": order["status"],
        }
        self.active_bot["deals"].append(take_profit_order)
        botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": take_profit_order }})
        if not botId:
            resp = jsonResp(
                {"message": "Failed to save take_profit deal in the bot", "botId": str(findId)},
                200,
            )
            return resp
        return order

    def short_base_order(self):
        pair = self.active_bot['pair']
        book_order = Book_Order(pair)
        qty = round_numbers((float(self.active_bot["base_order_size"])), 0)
        price = float(book_order.matching_engine(True, qty))
        self.price = price
        self.total_amount = qty

        # Avoid common rate limits
        if price:
            if price <= self.MIN_PRICE:
                return jsonResp_message("[Base order error] Price too low", 200)
        if qty <= self.MIN_QTY:
            return jsonResp_message("[Base order error] Quantity too low", 200)
        if (float(qty) * float(price)) <= self.MIN_NOTIONAL:
            return jsonResp_message("[Base order error] Price x Quantity too low", 200)

        if price:
            order = {
                "pair": pair,
                "qty": qty,
                "price": supress_notation(price),
            }
            res = requests.post(url=self.bb_sell_order_url, json=order)
        else:
            order = {
                "pair": pair,
                "qty": qty,
            }
            res = requests.post(url=self.bb_sell_market_order_url, json=order)

        if isinstance(handle_error(res), Response):
            return handle_error(res)
        res_order = res.json()

        base_deal = {
            "order_id": res_order["orderId"],
            "deal_type": "base_order",
            "active": "true",
            "strategy": "long",  # change accordingly
            "pair": res_order["symbol"],
            "order_side": res_order["side"],
            "order_type": res_order["type"],
            "price": res_order["price"],
            "qty": res_order["origQty"],
            "fills": res_order["fills"],
            "time_in_force": res_order["timeInForce"],
            "status": order["status"],
        }
        self.base_order_price = res_order["price"]

        self.active_bot["deals"].append(base_deal)
        botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": base_deal }})
        if botId:
            resp = jsonResp(
                {"message": "Failed to save take_profit deal in the bot", "botId": str(findId)},
                200,
            )
            return resp

        return base_deal

    def short_safety_order_generator(self, index):
        length = self.max_so_count
        so_deals = []
        while index < length:
            index += 1
            pair = self.active_bot['pair']
            qty = math.floor(self.division * 1000000) / 1000000
            price = float(Book_Order(pair).matching_engine(False, qty))

            order = {
                "pair": pair,
                "qty": qty,
                "price": price,
            }
            res = requests.post(url=self.bb_buy_order_url, data=json.dumps(order))
            if isinstance(handle_error(res), Response):
                return handle_error(res)
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
                "status": order["status"],
                "so_count": index
            }

            so_deals.append(safety_orders)

        self.active_bot["deals"].append(so_deals)
        botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": so_deals }})
        
        return so_deals

    def short_take_profit_order(self):
        pair = self.active_bot['pair']
        qty = round_numbers(self.total_amount, 0)
        market_price = float(Book_Order(pair).matching_engine(False, qty))
        price = round_numbers(market_price * (1 + float(self.active_bot["take_profit"]) / 100), 6)

        order = {
            "pair": pair,
            "qty": qty,
            "price": price,
        }
        res = requests.post(url=self.bb_tp_buy_order_url, json=order)
        if isinstance(handle_error(res), Response):
            return handle_error(res)
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
            "status": order["status"],
        }
        self.active_bot["deals"].append(tp_order)
        botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": tp_order }})

        if not botId:
            resp = jsonResp(
                {"message": "Failed to save take_profit deal in the bot", "botId": str(findId)},
                200,
            )
            return resp

        return tp_order

    def open_deal(self):
        new_deal = {"base_order": {}, "take_profit_order": {}, "so_orders": []}
        can_initialize = self.initialization()
        if isinstance(can_initialize, Response):
            return can_initialize

        # long_base_order = self.long_base_order()
        # if isinstance(long_base_order, Response):
        #     msg = long_base_order.json["message"]
        #     return jsonResp_message(msg, 200)
        # new_deal["base_order"] = long_base_order

        # Only do Safety orders if required
        if int(self.active_bot["max_so_count"]) > 0:
            long_safety_order_generator = self.long_safety_order_generator()
            if isinstance(long_safety_order_generator, Response):
                msg = long_safety_order_generator.json["message"]
                return jsonResp_message(msg, 200)
            new_deal["so_orders"] = long_safety_order_generator

        long_take_profit_order = self.long_take_profit_order()
        if isinstance(long_take_profit_order, Response):
            msg = long_take_profit_order.json["message"]
            return jsonResp_message(msg, 200)
        new_deal["take_profit_order"] = long_take_profit_order

        return

    def close_deals(self):
        """
        Close all deals
        - Deals should be stored as an array of orderIds
        - Delete (cancel) endpoint, with symbold and orderId
        """
        deals = self.active_bot["deals"]
        
        for d in deals:
            if "deal_type" in d and (d["status"] == "NEW" or d["status"] == "PARTIALLY_FILLED"):
                order_id = d["order_id"]
                res = requests.delete(url=f'{self.bb_close_order_url}/{self.active_bot["pair"]}/{order_id}')

                if isinstance(handle_error(res), Response):
                    return handle_error(res)
        
        # Sell everything
        pair = self.active_bot["pair"]
        base_asset = self.find_baseAsset(pair)
        balance = self.get_balances().json
        qty = round_numbers(float(next((s for s in symbols if s["symbol"] == symbol), None)["free"]), 0)
        book_order = Book_Order(pair)
        price = float(book_order.matching_engine(True, qty))

        if price:
            order = {
                "pair": pair,
                "qty": qty,
                "price": supress_notation(price),
            }
            res = requests.post(url=self.bb_sell_order_url, json=order)
        else:
            order = {
                "pair": pair,
                "qty": qty,
            }
            res = requests.post(url=self.bb_sell_market_order_url, json=order)

        if isinstance(handle_error(res), Response):
            return handle_error(res)

        response = jsonResp_message("Deals closed successfully", 200)
        return response
