import os
from decimal import Decimal

import requests
from api.account.models import Account
from api.charts.klines_sockets import KlineSockets
from api.orders.models.book_order import Book_Order, handle_error
from api.tools.jsonresp import jsonResp, jsonResp_message
from api.tools.round_numbers import round_numbers, supress_notation
from flask import Response
from flask import current_app as app


class Deal(Account):
    order_book_url = os.getenv("ORDER_BOOK")
    bb_base_url = f'{os.getenv("FLASK_DOMAIN")}'
    bb_buy_order_url = f"{bb_base_url}/order/buy"
    bb_tp_buy_order_url = f"{bb_base_url}/order/buy/take-profit"
    bb_buy_market_order_url = f"{bb_base_url}/order/buy/market"
    bb_sell_order_url = f"{bb_base_url}/order/sell"
    bb_tp_sell_order_url = f"{bb_base_url}/order/sell/take-profit"
    bb_sell_market_order_url = f"{bb_base_url}/order/sell/market"
    bb_opened_orders_url = f"{bb_base_url}/order/open"
    bb_close_order_url = f"{bb_base_url}/order/close"
    bb_stop_buy_order_url = f"{bb_base_url}/order/buy/stop-limit"
    bb_stop_sell_order_url = f"{bb_base_url}/order/sell/stop-limit"

    def __init__(self, bot, app):
        # Inherit also the __init__ from parent class
        super(self.__class__, self).__init__()

        self.active_bot = bot
        self.MIN_PRICE = float(
            self.price_filter_by_symbol(self.active_bot["pair"], "minPrice")
        )
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
        # PRICE_FILTER decimals
        self.price_precision = -(
            Decimal(
                str(self.price_filter_by_symbol(self.active_bot["pair"], "tickSize"))
            )
            .as_tuple()
            .exponent
        )
        self.qty_precision = -(
            Decimal(str(self.lot_size_by_symbol(self.active_bot["pair"], "stepSize")))
            .as_tuple()
            .exponent
        )
        self.deal = {
            "last_order_id": 0,
            "buy_price": "",
            "buy_total_qty": "",
            "current_price": "",
            "take_profit_price": "",
            "so_prices": [],
            "commission": 0,
        }

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

    def base_order(self):
        pair = self.active_bot["pair"]
        # Long position does not need qty in take_profit
        # initial price with 1 qty should return first match
        book_order = Book_Order(pair)
        initial_price = float(book_order.matching_engine(False, 1))
        qty = round_numbers(
            (float(self.active_bot["base_order_size"]) / float(initial_price)),
            self.qty_precision,
        )
        price = float(book_order.matching_engine(False, qty))
        self.price = price
        amount = float(qty) * float(price)
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
                "price": supress_notation(price, self.price_precision),
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
        # Remove follow line once redesign is finished
        self.base_order_price = order["price"]

        tp_price = (float(order["price"]) * 1 + (float(self.active_bot["take_profit"]) / 100))

        so_prices = {}
        so_num = 1
        for key, value in self.active_bot["safety_orders"].items():
            price = float(order["price"]) - (float(order["price"]) * (float(value["price_deviation_so"]) / 100))
            price = supress_notation(price, self.price_precision)
            so_prices[str(so_num)] = price
            so_num += 1

        deal = {
            "last_order_id": order["orderId"],
            "buy_price": order["price"],
            "buy_total_qty": order["origQty"],
            "current_price": self.get_ticker_price(order["symbol"]),
            "take_profit_price": tp_price,
            "safety_order_prices": so_prices,
            "commission": 0,
        }

        for chunk in order["fills"]:
            deal["commission"] += float(chunk["commission"])

        botId = app.db.bots.update_one(
            {"_id": self.active_bot["_id"]},
            {"$set": {"deal": deal}, "$push": {"orders": base_deal}},
        )
        if not botId:
            resp = jsonResp(
                {"message": "Failed to save Base order", "botId": str(self.active_bot["_id"])},
                200,
            )
            return resp

        return base_deal

    def long_take_profit_order(self):
        """
        Execute long strategy (buy and sell higher)
        take profit order (Binance take_profit)
        - We only have stop_price, because there are no book bids/asks in t0
        - Perform validations so we can avoid hitting endpoint errors
        - take_profit order can ONLY be executed once base order is filled (on Binance)
        """
        pair = self.active_bot["pair"]
        price = (1 + (float(self.active_bot["take_profit"]) / 100)) * float(
            self.active_bot["deal"]["buy_price"]
        )
        qty = round_numbers(
            self.active_bot["deal"]["buy_total_qty"], self.qty_precision
        )
        price = round_numbers(price, self.price_precision)

        # Validations
        if price:
            if price <= float(self.MIN_PRICE):
                return jsonResp_message("[Take profit order error] Price too low", 200)
        # Avoid common rate limits
        if qty <= float(self.MIN_QTY):
            return jsonResp_message("[Take profit order error] Quantity too low", 200)
        if price * qty <= float(self.MIN_NOTIONAL):
            return jsonResp_message(
                "[Take profit order error] Price x Quantity too low", 200
            )

        order = {
            "pair": pair,
            "qty": qty,
            "price": supress_notation(price, self.price_precision),
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
            "price": order["price"],
            "qty": order["origQty"],
            "fills": order["fills"],
            "time_in_force": order["timeInForce"],
            "status": order["status"],
        }
        self.active_bot["orders"].append(take_profit_order)
        botId = app.db.bots.update_one(
            {"_id": self.active_bot["_id"]},
            {
                "$set": {"deal.take_profit_price": order["price"]},
                "$push": {"orders": take_profit_order},
            },
        )
        if not botId:
            resp = jsonResp(
                {
                    "message": "Failed to save take_profit deal in the bot",
                    "botId": str(self.active_bot["_id"]),
                },
                200,
            )
            return resp
        return

    def short_stop_limit_order(self):
        """
        Part I of Short bot order: Stop loss (sell all)
        After safety orders are executed, if price keeps going down, execute Stop Loss order
        """
        pair = self.active_bot["pair"]
        base_asset = self.find_baseAsset(pair)
        base_order_deal = next(
            (
                bo_deal
                for bo_deal in self.active_bot["deals"]
                if bo_deal["deal_type"] == "base_order"
            ),
            None,
        )
        price = float(base_order_deal["price"])
        stop_loss = price * int(self.active_bot["stop_loss"]) / 100
        stop_loss_price = price - stop_loss
        self.asset_qty = next(
            (b["free"] for b in self.get_balances().json if b["asset"] == base_asset),
            None,
        )

        # Validations
        if price:
            if price <= float(self.MIN_PRICE):
                return jsonResp_message("[Short stop loss order] Price too low", 200)
        # Avoid common rate limits
        if float(self.asset_qty) <= float(self.MIN_QTY):
            return jsonResp_message("[Short stop loss order] Quantity too low", 200)
        if price * float(self.asset_qty) <= float(self.MIN_NOTIONAL):
            return jsonResp_message(
                "[Short stop loss order] Price x Quantity too low", 200
            )

        order = {
            "pair": pair,
            "qty": self.asset_qty,
            "price": supress_notation(
                stop_loss_price, self.price_precision
            ),  # Theoretically stop_price, as we don't have book orders
            "stop_price": supress_notation(stop_loss_price, self.price_precision),
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
        botId = app.db.bots.update_one(
            {"_id": self.active_bot["_id"]}, {"$push": {"deals": stop_limit_order}}
        )
        if not botId:
            resp = jsonResp(
                {
                    "message": "Failed to save short order stop_limit deal in the bot",
                    "botId": str(self.active_bot["_id"]),
                },
                200,
            )
            return resp

    def open_deal(self):
        order_errors = []
        can_initialize = self.initialization()
        if isinstance(can_initialize, Response):
            return can_initialize

        # If there is already a base order do not execute
        base_order_deal = next(
            (
                bo_deal
                for bo_deal in self.active_bot["orders"]
                if len(bo_deal) > 0 and (bo_deal["deal_type"] == "base_order")
            ),
            None,
        )
        if not base_order_deal:
            base_order = self.base_order()
            if isinstance(base_order, Response):
                msg = base_order.json["message"]
                order_errors.append({
                    "base_order_error": msg
                })
                return order_errors

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
        # Below take profit order goes first, because stream does not return a value
        # If there is already a take profit do not execute
        # If there is no base order can't execute
        bot = self.app.db.bots.find_one({"_id": self.active_bot["_id"]})
        check_bo = False
        check_tp = True
        for order in bot["orders"]:
            if len(order) > 0 and (order["deal_type"] == "base_order"):
                check_bo = True
            if len(order) > 0 and order["deal_type"] == "take_profit":
                check_tp = False

        if check_bo and check_tp:
            long_take_profit_order = self.long_take_profit_order()
            if isinstance(long_take_profit_order, Response):
                msg = long_take_profit_order.json["message"]
                order_errors.append(msg)

        # Subscribe to streams with corresponding symbol
        streams = KlineSockets()
        streams.start_stream()

        return order_errors

    def close_deals(self):
        """
        Close all deals
        - Deals should be stored as an array of orderIds
        - Delete (cancel) endpoint, with symbold and orderId
        """
        deals = self.active_bot["deals"]

        for d in deals:
            if "deal_type" in d and (
                d["status"] == "NEW" or d["status"] == "PARTIALLY_FILLED"
            ):
                order_id = d["order_id"]
                res = requests.delete(
                    url=f'{self.bb_close_order_url}/{self.active_bot["pair"]}/{order_id}'
                )

                if isinstance(handle_error(res), Response):
                    return handle_error(res)

        # Sell everything
        pair = self.active_bot["pair"]
        base_asset = self.find_baseAsset(pair)
        balance = self.get_balances().json
        qty = round_numbers(
            float(next((s for s in symbols if s["symbol"] == symbol), None)["free"]),
            self.qty_precision,
        )
        book_order = Book_Order(pair)
        price = float(book_order.matching_engine(True, qty))

        if price:
            order = {
                "pair": pair,
                "qty": qty,
                "price": supress_notation(price, self.price_precision),
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
