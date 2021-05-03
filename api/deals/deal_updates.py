import json
import math
import os
from decimal import Decimal

import requests
from api.account.models import Account
from api.orders.models.book_order import Book_Order, handle_error
from api.tools.jsonresp import jsonResp, jsonResp_message
from api.tools.round_numbers import round_numbers, supress_notation
from flask import Response
from flask import current_app as app


class DealUpdates(Account):

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
        self.price_precision = - (Decimal(str(self.price_filter_by_symbol(self.active_bot["pair"], "tickSize"))).as_tuple().exponent)
        self.qty_precision = - (Decimal(str(self.lot_size_by_symbol(self.active_bot["pair"], "stepSize"))).as_tuple().exponent)

    def update_take_profit(self, order_id):
        """
        Update take profit after websocket order endpoint triggered
        - Close current opened take profit order
        - Create new take profit order
        - Update database by replacing old take profit deal with new take profit deal
        """
        bot = self.active_bot
        for deal in bot["deals"]:
            if deal["order_id"] == order_id:
                so_deal_price = deal["price"]
                # Create new take profit order
                new_tp_price = float(so_deal_price) + (
                    float(so_deal_price) * float(bot["take_profit"]) / 100
                )
                asset = self.find_baseAsset(bot["pair"])

                # First cancel old order to unlock balance
                close_order_params = {"symbol": bot["pair"], "orderId": order_id}
                cancel_response = requests.post(
                    url=self.bb_close_order_url, params=close_order_params
                )
                if cancel_response.status_code != 200:
                    print("Take profit order not found, no need to cancel")
                else:
                    print("Old take profit order cancelled")

                qty = round_numbers(self.get_one_balance(asset), self.qty_precision)

                # Validations
                if new_tp_price:
                    if new_tp_price <= float(self.MIN_PRICE):
                        return jsonResp_message(
                            "[Take profit order error] Price too low", 200
                        )
                if qty <= float(self.MIN_QTY):
                    return jsonResp_message(
                        "[Take profit order error] Quantity too low", 200
                    )
                if new_tp_price * qty <= float(self.MIN_NOTIONAL):
                    return jsonResp_message(
                        "[Take profit order error] Price x Quantity too low", 200
                    )

                new_tp_order = {
                    "pair": bot["pair"],
                    "qty": qty,
                    "price": supress_notation(new_tp_price, self.price_precision),
                }
                res = requests.post(url=self.bb_sell_order_url, json=new_tp_order)
                if isinstance(handle_error(res), Response):
                    return handle_error(res)
                
                # New take profit order successfully created
                order = res.json()

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
                botId = app.db.bots.update_one(
                    {"_id": self.active_bot["_id"]},
                    {"$push": {"deals": take_profit_order}},
                )
                if not botId:
                    print(f"Failed to update take_profit deal: {botId}")
                else:
                    print(f"New take_profit deal successfully updated: {botId}")
                return
