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
        pair = self.active_bot['pair']
        length = self.max_so_count
        so_deals = []
        base_order_deal = next((bo_deal for bo_deal in self.active_bot["deals"] if bo_deal["deal_type"] == "base_order"), None)
        take_profit = float(self.active_bot["take_profit"])
        so_deviation = float(self.active_bot["price_deviation_so"]) / 100
        index = 0
        for index in range(length):
            index += 1

            # Stop price
            price = float(base_order_deal["price"]) - (so_deviation * float(base_order_deal["price"]))

            # Recursive order
            so_proportion = float(self.active_bot["so_size"]) / price
            qty = round_numbers(so_proportion, 0)

            order = {
                "pair": pair,
                "qty": qty,
                "price": supress_notation(price),
            }
            res = requests.post(url=self.bb_buy_order_url, json=order)
            if isinstance(handle_error(res), Response):
                return handle_error(res)

            response = res.json()

            safety_orders = {
                "order_id": response["clientOrderId"],
                "deal_type": "safety_order",
                "strategy": "long",  # change accordingly
                "pair": response["symbol"],
                "order_side": response["side"],
                "order_type": response["type"],
                "price": response["price"],
                "qty": response["origQty"],
                "fills": response["fills"],
                "time_in_force": response["timeInForce"],
                "so_count": index,
                "status": response["status"],
            }

            self.active_bot["deals"].append(safety_orders)
            botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": safety_orders }})
            if not botId:
                resp = jsonResp(
                    {"message": "Failed to save safety_order deal in the bot", "botId": str(findId)},
                    200,
                )
                return resp

            if index > length:
                break

        return

    def long_take_profit_order(self):
        """
        Execute long strategy (buy and sell higher)
        take profit order (Binance take_profit)
        - We only have stop_price, because there are no book bids/asks in t0
        - Perform validations so we can avoid hitting endpoint errors
        - take_profit order can ONLY be executed once base order is filled (on Binance)
        """
        pair = self.active_bot['pair']
        base_order_deal = next((bo_deal for bo_deal in self.active_bot["deals"] if bo_deal["deal_type"] == "base_order"), None)
        stop_price = (1 + (float(self.active_bot["take_profit"]) / 100)) * float(base_order_deal["price"])
        decimal_precision = self.get_quote_asset_precision(pair)
        qty = round_numbers(base_order_deal["qty"], 0)
        stop_price = round_numbers(stop_price, 6)
        real_price = stop_price - (stop_price * 0.01)

        # Validations
        if stop_price:
            if stop_price <= float(self.MIN_PRICE):
                return jsonResp_message("[Take profit order error] Price too low", 200)
        # Avoid common rate limits
        if qty <= float(self.MIN_QTY):
            return jsonResp_message("[Take profit order error] Quantity too low", 200)
        if stop_price * qty <= float(self.MIN_NOTIONAL):
            return jsonResp_message("[Take profit order error] Price x Quantity too low", 200)

        order = {
            "pair": pair,
            "qty": qty,
            "price": supress_notation(real_price), # Cheaper price to make it sellable
            "stop_price": supress_notation(stop_price),
        }
        res = requests.post(url=self.bb_tp_sell_order_url, json=order)
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
            "price": order["price"],
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
        return
    
    def update_take_profit(self, order_id):
        """
        Update take profit after websocket order endpoint triggered
        - Close current opened take profit order
        - Create new take profit order
        - Update database by replacing old take profit deal with new take profit deal
        """
        bot = self.active_bot
        for deal in bot["deals"]:
            if deal == order_id:
                so_deal_price = deal["price"]
                # Create new take profit order
                new_tp_price = float(so_deal_price) + (float(so_deal_price) * float(bot["take_profit"]) / 100)
                asset = self.find_baseAsset(bot["pair"])
                qty = self.get_one_balance(asset)

                # Validations
                if new_tp_price:
                    if new_tp_price <= float(self.MIN_PRICE):
                        return jsonResp_message("[Take profit order error] Price too low", 200)
                if qty <= float(self.MIN_QTY):
                    return jsonResp_message("[Take profit order error] Quantity too low", 200)
                if new_tp_price * qty <= float(self.MIN_NOTIONAL):
                    return jsonResp_message("[Take profit order error] Price x Quantity too low", 200)

                new_tp_order = {
                    "pair": bot["pair"],
                    "qty": qty,
                    "price": supress_notation(new_tp_price),
                }
                res = requests.post(url=self.bb_tp_sell_order_url, json=new_tp_order)
                order = res.json()

                # New take profit order successfully created
                # Now cancel old
                close_order_params = {
                    "symbol": bot["pair"],
                    "orderId": order_id
                }
                cancel_response = requests.post(url=self.bb_close_order_url, params=close_order_params)
                canceled_order = res.json()
                if canceled_order:
                    print("Old take profit order cancelled")
                
                # Replace take_profit order
                take_profit_deal = {
                    "deal_type": "take_profit",
                    "order_id": order["orderId"],
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
                # Build new deals list
                new_deals = []
                for d in bot["deals"]:
                    if d["deal_type"] != "take_profit":
                        new_deals.append(d)
                
                # Append now new take_profit deal
                new_deals.append(take_profit_deal)
                self.active_bot["deals"] = new_deals
                botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": take_profit_order }})
                if not botId:
                    print(f"Failed to update take_profit deal: {botId}")
                else:
                    print(f"New take_profit deal successfully updated: {botId}")
                return
    
    def short_stop_limit_order(self):
        """
        Part I of Short bot order: Stop loss (sell all)
        After safety orders are executed, if price keeps going down, execute Stop Loss order
        """
        pair = self.active_bot['pair']
        base_asset = self.find_baseAsset(pair)
        base_order_deal = next((bo_deal for bo_deal in self.active_bot["deals"] if bo_deal["deal_type"] == "base_order"), None)
        price = float(base_order_deal["price"])
        stop_loss = price * int(self.active_bot["stop_loss"]) / 100
        stop_loss_price = price - stop_loss
        self.asset_qty = next((b["free"] for b in self.get_balances().json if b["asset"] == base_asset), None)

        # Validations
        if price:
            if price <= float(self.MIN_PRICE):
                return jsonResp_message("[Short stop loss order] Price too low", 200)
        # Avoid common rate limits
        if float(self.asset_qty) <= float(self.MIN_QTY):
            return jsonResp_message("[Short stop loss order] Quantity too low", 200)
        if price * float(self.asset_qty) <= float(self.MIN_NOTIONAL):
            return jsonResp_message("[Short stop loss order] Price x Quantity too low", 200)

        order = {
            "pair": pair,
            "qty": self.asset_qty,
            "price": supress_notation(stop_loss_price), # Theoretically stop_price, as we don't have book orders
            "stop_price": supress_notation(stop_loss_price),
        }
        res = requests.post(url=self.bb_stop_sell_order_url, json=order)
        if isinstance(handle_error(res), Response):
            return handle_error(res)
        
        stop_limit_order = res.json()

        stop_limit_order = {
            "deal_type": "stop_limit",
            "order_id": stop_limit_order["orderId"],
            "strategy": "long",  # change accordingly
            "pair": stop_limit_order["symbol"],
            "order_side": stop_limit_order["side"],
            "order_type": stop_limit_order["type"],
            "price": stop_limit_order["price"],
            "qty": stop_limit_order["origQty"],
            "fills": stop_limit_order["fills"],
            "time_in_force": stop_limit_order["timeInForce"],
            "status": stop_limit_order["status"],
        }

        self.active_bot["deals"].append(stop_limit_order)
        botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": stop_limit_order }})
        if not botId:
            resp = jsonResp(
                {"message": "Failed to save short order stop_limit deal in the bot", "botId": str(findId)},
                200,
            )
            return resp

    def short_base_order(self):
        """
        Part II of Short bot order: Short sell buy back order
        After safety orders are executed, if price keeps going down, execute Stop Loss order
        Then execute this short base order to buy back
        This order replaces the initial base order
        """
        # Buy back order
        pair = self.active_bot['pair']
        base_asset = self.find_baseAsset(pair)
        base_order_deal = next((bo_deal for bo_deal in self.active_bot["deals"] if bo_deal["deal_type"] == "base_order"), None)
        price = float(base_order_deal["price"])
        short_order = price * int(self.active_bot["short_stop_price"]) / 100
        stop_loss_price = price - short_order
        

        order = {
            "pair": pair,
            "qty": self.asset_qty,
            "price": supress_notation(price), # Theoretically stop_price, as we don't have book orders
            "stop_price": supress_notation(price),
        }
        res = requests.post(url=self.bb_stop_buy_order_url, json=order)
        if isinstance(handle_error(res), Response):
            return handle_error(res)
        order = res.json()

        short_order = {
            "deal_type": "short_order",
            "order_id": order["orderId"],
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
        self.active_bot["deals"].append(short_order)
        botId = app.db.bots.update_one({"_id": self.active_bot["_id"]}, {"$push": {"deals": short_order }})
        if not botId:
            resp = jsonResp(
                {"message": "Failed to save short deal in the bot", "botId": str(findId)},
                200,
            )
            return resp
        return order


    def open_deal(self):
        order_errors = []
        can_initialize = self.initialization()
        if isinstance(can_initialize, Response):
            return can_initialize

        # If there is already a base order do not execute
        base_order_deal = next((bo_deal for bo_deal in self.active_bot["deals"] if len(bo_deal) > 0 and (bo_deal["deal_type"] == "base_order")), None)
        if not base_order_deal:
            long_base_order = self.long_base_order()
            if isinstance(long_base_order, Response):
                msg = long_base_order.json["message"]
                return jsonResp_message(msg, 200)

        # Only do Safety orders if required
        if int(self.active_bot["max_so_count"]) > 0:
            long_safety_order_generator = self.long_safety_order_generator()
            if isinstance(long_safety_order_generator, Response):
                msg = long_safety_order_generator.json["message"]
                order_errors.append(msg)

        long_take_profit_order = self.long_take_profit_order()
        if isinstance(long_take_profit_order, Response):
            msg = long_take_profit_order.json["message"]
            order_errors.append(msg)

        # If short order is enabled 
        if float(self.active_bot["short_order"]) > 0:
            short_stop_limit_order = self.short_stop_limit_order()
            if isinstance(short_stop_limit_order, Response):
                msg = short_stop_limit_order.json["message"]
                order_errors.append(msg)

            short_order = self.short_base_order()
            if isinstance(short_order, Response):
                msg = short_order.json["message"]
                order_errors.append(msg)

        return True, order_errors

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
