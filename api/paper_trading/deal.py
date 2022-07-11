from decimal import Decimal
from time import time

import requests
from api.account.account import Account
from api.deals.schema import DealSchema
from api.orders.models.book_order import Book_Order, handle_error
from api.tools.handle_error import bot_errors, handle_binance_errors, jsonResp
from api.tools.round_numbers import round_numbers, supress_notation
from bson.objectid import ObjectId
from flask import Response
from flask import current_app as app


class TestDeal(Account):
    """
    Simulated deal    
    """
    def __init__(self, bot):
        # Inherit from parent class
        self.active_bot = bot
        id = str(ObjectId())
        self.order = {
            "symbol": "BTCUSDT",
            "orderId": id,
            "orderListId": -1,
            "clientOrderId": id,
            "transactTime": time() * 1000,
            "price": "0.00000000",
            "origQty": "10.00000000",
            "executedQty": "10.00000000",
            "cummulativeQuoteQty": "10.00000000",
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": "SELL",
            "fills": []
        }
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
        self.deal = DealSchema()
    
    def simulate_order(self, pair, price, qty, side):
        self.order["symbol"] = pair
        self.order["price"] = price
        self.order["origQty"] = qty
        self.order["executedQty"] = qty
        self.order["cummulativeQuoteQty"] = qty
        self.order["side"] = side
        return self.order


    def get_one_balance(self, symbol="BTC"):
        # Response after request
        data = self.bb_request(url=self.bb_balance_url)
        symbol_balance = next(
            (x["free"] for x in data["data"] if x["asset"] == symbol), None
        )
        return symbol_balance

    def base_order(self):
        """
        Required initial order to trigger bot.
        Other orders require this to execute,
        therefore should fail if not successful
        """

        pair = self.active_bot["pair"]

        # Long position does not need qty in take_profit
        # initial price with 1 qty should return first match
        book_order = Book_Order(pair)
        initial_price = float(book_order.matching_engine(False))
        qty = round_numbers(
            (float(self.active_bot["base_order_size"]) / float(initial_price)),
            self.qty_precision,
        )
        price = float(book_order.matching_engine(False, qty))

        if price:
            res = self.simulate_order(pair, supress_notation(price, self.price_precision), qty, "BUY")
        else:
            res = self.simulate_order(pair, supress_notation(initial_price, self.price_precision), qty, "BUY")

        # If error pass it up to parent function, can't continue
        if "error" in res:
            return res

        base_deal = {
            "timestamp": res["transactTime"],
            "order_id": res["orderId"],
            "deal_type": "base_order",
            "pair": res["symbol"],
            "order_side": res["side"],
            "order_type": res["type"],
            "price": res["price"],
            "qty": res["origQty"],
            "fills": res["fills"],
            "time_in_force": res["timeInForce"],
            "status": res["status"],
        }

        tp_price = float(res["price"]) * 1 + (
            float(self.active_bot["take_profit"]) / 100
        )

        so_prices = {}
        so_num = 1
        for key, value in self.active_bot["safety_orders"].items():
            price = float(res["price"]) - (
                float(res["price"]) * (float(value["price_deviation_so"]) / 100)
            )
            price = supress_notation(price, self.price_precision)
            so_prices[str(so_num)] = price
            so_num += 1

        deal = {
            "last_order_id": res["orderId"],
            "buy_timestamp": res["transactTime"],
            "buy_price": res["price"],
            "buy_total_qty": res["origQty"],
            "current_price": res["price"],
            "take_profit_price": tp_price,
            "safety_order_prices": so_prices,
        }

        botId = app.db.paper_trading.update_one(
            {"_id": self.active_bot["_id"]},
            {
                "$push": {"orders": base_deal},
                "$set": {"deal": deal }
            },
        )

        if not botId:
            resp = jsonResp(
                {
                    "message": "Failed to save Base order",
                    "botId": str(self.active_bot["_id"]),
                },
                200,
            )
            return resp

        return base_deal

    def take_profit_order(self):
        """
        take profit order (Binance take_profit)
        - We only have stop_price, because there are no book bids/asks in t0
        - Perform validations so we can avoid hitting endpoint errors
        - take_profit order can ONLY be executed once base order is filled (on Binance)
        """
        pair = self.active_bot["pair"]
        updated_bot = app.db.paper_trading.find_one({"_id": self.active_bot["_id"]})
        deal_buy_price = updated_bot["deal"]["buy_price"]
        buy_total_qty = updated_bot["deal"]["buy_total_qty"]
        price = (1 + (float(self.active_bot["take_profit"]) / 100)) * float(
            deal_buy_price
        )
        qty = supress_notation(buy_total_qty, self.qty_precision)
        price = supress_notation(price, self.price_precision)

        if price:
            res = self.simulate_order(pair, supress_notation(price, self.price_precision), qty, "SELL")
        else:
            price = (1 + (float(self.active_bot["take_profit"]) / 100)) * float(
                deal_buy_price
            )
            res = self.simulate_order(pair, supress_notation(price, self.price_precision), qty, "SELL")
        # If error pass it up to parent function, can't continue
        if "error" in res:
            return res

        take_profit_order = {
            "deal_type": "take_profit",
            "order_id": res["orderId"],
            "pair": res["symbol"],
            "order_side": res["side"],
            "order_type": res["type"],
            "price": res["price"],
            "qty": res["origQty"],
            "fills": res["fills"],
            "time_in_force": res["timeInForce"],
            "status": res["status"],
        }

        self.active_bot["orders"].append(take_profit_order)
        botId = app.db.paper_trading.update_one(
            {"_id": self.active_bot["_id"]},
            {
                "$set": {"deal.take_profit_price": res["price"]},
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

    def trailling_profit(self):
        updated_bot = app.db.paper_trading.find_one({"_id": self.active_bot["_id"]})
        deal_buy_price = updated_bot["deal"]["buy_price"]
        price = (1 + (float(self.active_bot["take_profit"]) / 100)) * float(
            deal_buy_price
        )
        price = supress_notation(price, self.price_precision)
        botId = app.db.paper_trading.update_one(
            {"_id": self.active_bot["_id"]},
            {"$set": {"deal.take_profit_price": price, "deal.trailling_profit": price}},
        )
        if not botId:
            resp = jsonResp(
                {
                    "message": "Failed to save trailling deviation",
                    "botId": str(self.active_bot["_id"]),
                },
                200,
            )
            return resp

    def open_deal(self):
        order_errors = []

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
                order_errors.append({"base_order_error": msg})
                return order_errors

        # Below take profit order goes first, because stream does not return a value
        # If there is already a take profit do not execute
        # If there is no base order can't execute
        bot = app.db.paper_trading.find_one({"_id": self.active_bot["_id"]})
        check_bo = False
        check_tp = True
        for order in bot["orders"]:
            if len(order) > 0 and (order["deal_type"] == "base_order"):
                check_bo = True
            if len(order) > 0 and order["deal_type"] == "take_profit":
                check_tp = False

        if check_bo and check_tp:
            if bot["trailling"] == "true":
                take_profit_order = self.trailling_profit()
            else:
                take_profit_order = self.take_profit_order()

            if isinstance(take_profit_order, Response):
                msg = take_profit_order.json["message"]
                order_errors.append(msg)

        # Update stop loss regarless of base order
        if "stop_loss" in bot and float(bot["stop_loss"]) > 0:
            buy_price = float(bot["deal"]["buy_price"])
            stop_loss_price = buy_price - (buy_price * float(bot["stop_loss"]) / 100)
            bot["deal"]["stop_loss"] = supress_notation(
                stop_loss_price, self.price_precision
            )
        
        # Keep trailling_stop_loss_price up to date in case of failure to update in autotrade
        if "deal" in bot:
            if "trailling_stop_loss_price" in bot["deal"]:

                take_profit = float(bot["deal"]["trailling_profit"]) * (
                    1 + (float(bot["take_profit"]) / 100)
                )
                # Update trailling_stop_loss
                bot["deal"]["trailling_stop_loss_price"] = float(
                    take_profit
                ) - (
                    float(take_profit)
                    * (float(bot["trailling_deviation"]) / 100)
                )

            try:
                app.db.paper_trading.update_one(
                    {"_id": bot["_id"]}, {"$set": {"deal": bot["deal"]}}
                )
            except Exception as e:
                order_errors.append(e)

        return order_errors

    def close_all(self):
        """
        Close all deals and sell pair
        1. Close all deals
        2. Sell Coins
        3. Delete bot
        """
        orders = self.active_bot["orders"]

        # Close all active orders
        if len(orders) > 0:
            for d in orders:
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
        balance = self.get_one_balance(base_asset)
        if balance:
            qty = round_numbers(balance, self.qty_precision)
            book_order = Book_Order(pair)
            price = float(book_order.matching_engine(True, qty))

            if price:
                order = {
                    "pair": pair,
                    "qty": qty,
                    "price": supress_notation(price, self.price_precision),
                }
                res = self.bb_request(
                    method="POST", url=self.bb_sell_order_url, payload=order
                )
            else:
                order = {
                    "pair": pair,
                    "qty": qty,
                }
                res = self.bb_request(
                    method="POST", url=self.bb_sell_market_order_url, payload=order
                )

            # Continue even if there are errors
            handle_binance_errors(res)

        return
