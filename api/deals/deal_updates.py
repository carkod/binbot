from decimal import Decimal

import requests
from api.app import create_app
from api.deals.models import Deal
from api.orders.models.book_order import Book_Order, handle_error
from api.tools.handle_error import handle_binance_errors
from api.tools.handle_error import jsonResp, jsonResp_message
from api.tools.round_numbers import round_numbers, supress_notation
from flask import Response


class DealUpdates(Deal):
    def __init__(self, bot):

        self.active_bot = bot
        self.MIN_PRICE = float(
            self.price_filter_by_symbol(self.active_bot["pair"], "minPrice")
        )
        self.MIN_QTY = float(self.lot_size_by_symbol(self.active_bot["pair"], "minQty"))
        self.MIN_NOTIONAL = float(self.min_notional_by_symbol(self.active_bot["pair"]))
        self.app = create_app()
        self.order = {
            "order_id": "",
            "deal_type": "base_order",
            "status": "active",
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
    
    def _compute_qty(self, pair):
        """
        Helper function to compute buy_price.
        Previous qty = bot["deal"]["buy_total_qty"]
        """

        asset = self.find_baseAsset(pair)
        qty = round_numbers(self.get_one_balance(asset), self.qty_precision)
        return qty

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
                take_profit_order = {
                    "deal_type": "take_profit",
                    "order_id": order["orderId"],
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
                new_deals.append(take_profit_order)
                self.active_bot["orders"] = new_deals
                botId = self.app.db.bots.update_one(
                    {"_id": self.active_bot["_id"]},
                    {"$push": {"orders": take_profit_order}},
                )
                if not botId:
                    print(f"Failed to update take_profit deal: {botId}")
                else:
                    print(f"New take_profit deal successfully updated: {botId}")
                return

    def so_update_deal(self, so_index):
        """
        Executes when
        - Klines websocket triggers condition price = safety order price
        - Get qty and price (use trade books so it can sell immediately at limit)
        - Update deal.price, deal.qty
        - Cancel old take profit order
        - Update DB with new deal data
        - Create new take profit order
        - Update DB with new take profit deal data
        """
        pair = self.active_bot["pair"]
        so_qty = list(self.active_bot["safety_orders"].values())[int(so_index) - 1][
            "so_size"
        ]
        book_order = Book_Order(pair)
        price = float(book_order.matching_engine(False, so_qty))
        qty = round_numbers(
            (float(so_qty) / float(price)),
            self.qty_precision,
        )

        order = {
            "pair": pair,
            "qty": supress_notation(qty, self.qty_precision),
            "price": supress_notation(price, self.price_precision),
        }
        res = requests.post(url=self.bb_buy_order_url, json=order)
        if isinstance(handle_error(res), Response):
            return handle_error(res)

        response = res.json()

        safety_order = {
            "order_id": response["orderId"],
            "deal_type": "safety_order",
            "pair": response["symbol"],
            "order_side": response["side"],
            "order_type": response["type"],
            "price": response["price"],
            "qty": response["origQty"],
            "fills": response["fills"],
            "time_in_force": response["timeInForce"],
            "so_count": so_index,
            "status": response["status"],
        }

        self.active_bot["orders"].append(safety_order)
        new_tp_price = float(response["price"]) * (
            1 + float(self.active_bot["take_profit"]) / 100
        )

        commission = 0
        for chunk in response["fills"]:
            commission += float(chunk["commission"])

        if "buy_total_qty" in self.active_bot["deal"]:
            buy_total_qty = float(self.active_bot["deal"]["buy_total_qty"]) + float(
                response["origQty"]
            )
        else:
            buy_total_qty = self.active_bot["base_order_size"]

        new_so_prices = supress_notation(
            self.active_bot["deal"]["safety_order_prices"][so_index],
            self.price_precision,
        )
        del self.active_bot["deal"]["safety_order_prices"][so_index]

        key_to_remove = list(self.active_bot["safety_orders"].keys())[int(so_index) - 1]
        del self.active_bot["safety_orders"][key_to_remove]

        # New take profit order
        self.active_bot["deal"]["take_profit_price"] = new_tp_price
        order_id = None
        for order in self.active_bot["orders"]:
            if order["deal_type"] == "take_profit":
                order_id = order["order_id"]
                self.active_bot["orders"].remove(order)
                break

        if order_id:
            # First cancel old order to unlock balance
            cancel_response = requests.delete(
                url=f"{self.bb_close_order_url}/{self.active_bot['pair']}/{order_id}"
            )
            if cancel_response.status_code != 200:
                print("Take profit order not found, no need to cancel")
            else:
                print("Old take profit order cancelled")

            qty = round_numbers(
                self.active_bot["deal"]["buy_total_qty"], self.qty_precision
            )
            new_tp_order = {
                "pair": self.active_bot["pair"],
                "qty": qty,
                "price": supress_notation(new_tp_price, self.price_precision),
            }
            res = requests.post(url=self.bb_sell_order_url, json=new_tp_order)
            if isinstance(handle_error(res), Response):
                return handle_error(res)

            # New take profit order successfully created
            tp_response = res.json()

            # Replace take_profit order
            take_profit_order = {
                "deal_type": "take_profit",
                "order_id": tp_response["orderId"],
                "pair": tp_response["symbol"],
                "order_side": tp_response["side"],
                "order_type": tp_response["type"],
                "price": tp_response["price"],
                "qty": tp_response["origQty"],
                "fills": tp_response["fills"],
                "time_in_force": tp_response["timeInForce"],
                "status": tp_response["status"],
            }

            self.active_bot["orders"].append(take_profit_order)

        botId = self.self.app.db.bots.update_one(
            {"_id": self.active_bot["_id"]},
            {
                "$set": {
                    "deal.buy_price": supress_notation(
                        response["price"], self.price_precision
                    ),
                    "deal.take_profit_price": supress_notation(
                        new_tp_price, self.price_precision
                    ),
                    "deal.buy_total_qty": supress_notation(
                        buy_total_qty, self.qty_precision
                    ),
                    "deal.safety_order_prices": new_so_prices,
                    "safety_orders": self.active_bot["safety_orders"],
                    "orders": self.active_bot["orders"],
                },
                "$inc": {"deal.comission": commission},
            },
        )
        if not botId:
            resp = jsonResp(
                {
                    "message": "Failed to save safety_order deal in the bot",
                    "botId": str(self.active_bot["_id"]),
                },
                200,
            )
            return resp
        return

    def update_stop_limit(self, price):
        """
        Update stop limit after websocket
        - Sell initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot
        """
        bot = self.active_bot
        qty = self._compute_qty(bot["pair"])
        book_order = Book_Order(bot["pair"])
        price = float(book_order.matching_engine(False, qty))

        order_id = None
        for order in bot["orders"]:
            if order["deal_type"] == "take_profit":
                order_id = order["order_id"]
                bot["orders"].remove(order)
                break

        if order_id:
            # First cancel old order to unlock balance
            cancel_response = requests.delete(
                url=f"{self.bb_close_order_url}/{self.active_bot['pair']}/{order_id}"
            )
            if cancel_response.status_code != 200:
                print("Take profit order not found, no need to cancel")
            else:
                print("Old take profit order cancelled")

        stop_limit_order = {
            "pair": bot["pair"],
            "qty": qty,
            "price": supress_notation(price, self.price_precision),
        }
        res = requests.post(url=self.bb_sell_order_url, json=stop_limit_order)
        if isinstance(handle_error(res), Response):
            error = res.json()["msg"]
            botId = self.app.db.bots.update_one(
                {"_id": bot["_id"]},
                {"$push": {"errors": error}, "$set": {"status": "error"}},
            )
            return handle_error(res)

        # Append now stop_limit deal
        stop_limit_response = {
            "deal_type": "stop_limit",
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
        new_orders = bot["orders"]
        new_orders.append(stop_limit_response)
        botId = self.app.db.bots.update_one(
            {"_id": bot["_id"]},
            {"$push": {"orders": new_orders}, "$set": {"status": "loss"}},
        )
        if not botId:
            print(f"Failed to update stop_limit deal: {botId}")
        else:
            buy_gbp_result = self.buy_gbp_balance()
            print(f"New stop_limit deal successfully updated: {botId}")
        return

    def trailling_stop_loss(self, price):
        """
        Update stop limit after websocket
        - Sell initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot
        """
        bot = self.active_bot
        qty = self._compute_qty(bot["pair"])
        book_order = Book_Order(bot["pair"])
        price = float(book_order.matching_engine(False, qty))

        trailling_stop_loss = {
            "pair": bot["pair"],
            "qty": qty,
            "price": supress_notation(price, self.price_precision),
        }
        res = requests.post(url=self.bb_sell_order_url, json=trailling_stop_loss)
        result = handle_binance_errors(res)
        if result["error"] == 1:
            error_message = f'Trailling stop loss error: {result["message"]}'
            self.app.db.bots.find_one_and_update(
                {"pair": bot["pair"]},
                {"$push": {"errors": error_message}, "$set": {"status": "error"}},
            )
            return "completed"
        else:
            # Append now stop_limit deal
            trailling_stop_loss_response = {
                "deal_type": "stop_limit",
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
            bot["orders"].append(trailling_stop_loss_response)
            botId = self.app.db.bots.update_one(
                {"_id": bot["_id"]},
                {
                    "$set": {
                        "status": "completed",
                        "deal.take_profit_price": res["price"],
                        "orders": bot["orders"]
                    },
                },
            )
            if botId:
                buy_gbp_result = self.buy_gbp_balance()
                print("Successfully finished take profit trailling!")
                return "completed"
        return
