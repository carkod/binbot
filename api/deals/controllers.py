from decimal import Decimal
from time import time
import uuid

import requests
from api.account.account import Account
from api.bots.models import BotModel
from api.bots.schemas import BotSchema
from api.deals.models import DealModel, OrderModel
from api.deals.schema import DealSchema, OrderSchema
from api.orders.models.book_order import Book_Order, handle_error
from api.tools.exceptions import (
    BaseDealError,
    OpenDealError,
    TakeProfitError,
    TraillingProfitError,
)
from api.tools.handle_error import QuantityTooLow, handle_binance_errors, jsonResp_error_message
from api.tools.round_numbers import round_numbers, supress_notation
from flask import current_app as app, Response
from pymongo import ReturnDocument
from api.app import create_app
from marshmallow.exceptions import ValidationError
from requests.exceptions import HTTPError


class CreateDealController(Account):
    """
    Centralized deal controller.

    This is the first step that comes after a bot is saved
    1. Save bot
    2. Open deal (deal controller)
    3. Update deals (deal update controller)

    - db_collection = ["bots", "paper_trading"].
    paper_trading uses simulated orders and bot uses real binance orders
    """

    def __init__(self, bot, db_collection="paper_trading"):
        # Inherit from parent class
        self.active_bot = BotModel(**bot)
        self.app = create_app()
        self.db_collection = self.app.db[db_collection]
        self.decimal_precision = self.get_quote_asset_precision(self.active_bot.pair)
        # PRICE_FILTER decimals
        self.price_precision = -(
            Decimal(str(self.price_filter_by_symbol(self.active_bot.pair, "tickSize")))
            .as_tuple()
            .exponent
        )
        self.qty_precision = -(
            Decimal(str(self.lot_size_by_symbol(self.active_bot.pair, "stepSize")))
            .as_tuple()
            .exponent
        )
    
    def generate_id(self):
        return uuid.uuid4().hex

    def simulate_order(self, pair, price, qty, side):
        order = {
            "symbol": pair,
            "orderId": self.generate_id(),
            "orderListId": -1,
            "clientOrderId": self.generate_id(),
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": [],
        }
        return order

    def simulate_response_order(self, pair, price, qty, side):
        response_order = {
            "symbol": pair,
            "orderId": id,
            "orderListId": -1,
            "clientOrderId": id,
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": [],
        }
        return response_order

    def get_one_balance(self, symbol="BTC"):
        # Response after request
        data = self.bb_request(url=self.bb_balance_url)
        symbol_balance = next(
            (x["free"] for x in data["data"] if x["asset"] == symbol), None
        )
        return symbol_balance

    def compute_qty(self, pair):
        """
        Helper function to compute buy_price.
        Previous qty = bot.deal["buy_total_qty"]
        """

        asset = self.find_baseAsset(pair)
        balance = self.get_one_balance(asset)
        if not balance:
            return None
        qty = round_numbers(balance, self.qty_precision)
        return qty

    def update_deal_logs(self, msg):
        self.db_collection.update_one(
            {"_id": self.active_bot._id},
            {"$push": {"errors": msg}},
        )
        return msg
    
    def base_order(self):
        """
        Required initial order to trigger bot.
        Other orders require this to execute,
        therefore should fail if not successful
        """

        pair = self.active_bot.pair

        # Long position does not need qty in take_profit
        # initial price with 1 qty should return first match
        book_order = Book_Order(pair)
        initial_price = float(book_order.matching_engine(False))
        qty = round_numbers(
            (float(self.active_bot.base_order_size) / float(initial_price)),
            self.qty_precision,
        )
        price = float(book_order.matching_engine(False, qty))

        if not price:
            price = initial_price

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(
                pair, supress_notation(price, self.price_precision), qty, "BUY"
            )
        else:
            order = {
                "pair": pair,
                "qty": qty,
                "price": supress_notation(price, self.price_precision),
            }
            res = self.bb_request(
                method="POST", url=self.bb_buy_order_url, payload=order
            )

        order_data = OrderModel(
            timestamp=res["transactTime"],
            order_id=res["orderId"],
            deal_type="base_order",
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res["price"],
            qty=res["origQty"],
            fills=res["fills"],
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.orders.append(order_data)
        tp_price = float(res["price"]) * 1 + (float(self.active_bot.take_profit) / 100)

        self.active_bot.deal = DealModel(
            buy_timestamp=res["transactTime"],
            buy_price=res["price"],
            buy_total_qty=res["origQty"],
            current_price=res["price"],
            take_profit_price=tp_price,
        )

        try:
            bot_schema = BotSchema()
            bot = bot_schema.dump(self.active_bot)
            bot.pop("_id")

            bot = self.db_collection.find_one_and_update(
                {"_id": self.active_bot._id},
                {"$set": bot},
                return_document=ReturnDocument.AFTER,
            )
        except ValidationError as error:
            raise BaseDealError(error.messages)
        except (TypeError, AttributeError) as error:
            message = str(";".join(error.args))
            raise BaseDealError(message)
        except Exception as error:
            raise BaseDealError(error)

        return bot

    def take_profit_order(self, deal_data):
        """
        take profit order (Binance take_profit)
        - We only have stop_price, because there are no book bids/asks in t0
        - take_profit order can ONLY be executed once base order is filled (on Binance)
        """

        deal_buy_price = deal_data.buy_price
        buy_total_qty = deal_data.buy_total_qty
        price = (1 + (float(bot.take_profit) / 100)) * float(deal_buy_price)

        if self.db_collection.name == "paper_trading":
            qty = bot.deal.buy_total_qty
        else:
            qty = self.compute_qty(bot.pair)
            
        qty = supress_notation(buy_total_qty, self.qty_precision)
        price = supress_notation(price, self.price_precision)


        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(bot.pair, price, qty, "SELL")
            if price:
                res = self.simulate_order(
                    self.active_bot.pair,
                    price,
                    qty,
                    "SELL",
                )
            else:
                price = (1 + (float(bot.take_profit) / 100)) * float(deal_buy_price)
                res = self.simulate_order(
                    self.active_bot.pair,
                    price,
                    qty,
                    "SELL",
                )
        else:
            if price:
                tp_order = {
                    "pair": bot.pair,
                    "qty": supress_notation(qty, self.qty_precision),
                    "price": supress_notation(price, self.price_precision),
                }
                res = self.bb_request(
                    method="POST", url=self.bb_sell_order_url, payload=tp_order
                )
            else:
                tp_order = {"pair": bot.pair, "qty": supress_notation(qty, self.qty_precision)}
                res = self.bb_request(
                    method="POST",
                    url=self.bb_sell_market_order_url,
                    payload=tp_order,
                )
        
        # If error pass it up to parent function, can't continue
        if "error" in res:
            raise TakeProfitError(res["error"])

        order_data = OrderModel(
            timestamp=res["transactTime"],
            order_id=res["orderId"],
            deal_type="take_profit",
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res["price"],
            qty=res["origQty"],
            fills=res["fills"],
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.take_profit_price = res["price"]

        try:
            bot_schema = BotSchema()
            bot = bot_schema.dump(self.active_bot)

            bot = self.db_collection.find_one_and_update(
                {"_id": self.active_bot._id},
                {
                    "$set": {"deal.take_profit_price": res["price"]},
                    "$push": {"orders": take_profit_deal},
                },
                return_document=ReturnDocument.AFTER,
            )
        except Exception as error:
            raise TakeProfitError(error)

        return bot

    def trailling_profit(self, current_price):
        """
        Sell at take_profit price, because prices will not reach trailling
        """

        try:
            bot = self.active_bot
            deal_data = self.active_bot.deal
            deal_buy_price = deal_data.buy_price
            price = (1 + (float(self.active_bot.take_profit) / 100)) * float(
                deal_buy_price
            )
            deal_data.take_profit_price = price
            deal_data.trailling_profit = price


            if self.db_collection.name == "paper_trading":
                qty = deal_data.buy_total_qty
            else:
                qty = self.compute_qty(bot.pair)


            # Dispatch fake order
            if self.db_collection.name == "paper_trading":
                res = self.simulate_order(bot.pair, price, qty, "SELL")
                if price:
                    res = self.simulate_order(
                        self.active_bot.pair,
                        price,
                        qty,
                        "SELL",
                    )
                else:
                    price = current_price
                    res = self.simulate_order(
                        self.active_bot.pair,
                        price,
                        qty,
                        "SELL",
                    )
            # Dispatch real order
            else:
                if price:
                    tp_order = {
                        "pair": bot.pair,
                        "qty": supress_notation(qty, self.qty_precision),
                        "price": supress_notation(price, self.price_precision),
                    }
                    res = self.bb_request(
                        method="POST", url=self.bb_sell_order_url, payload=tp_order
                    )
                else:
                    tp_order = {"pair": bot.pair, "qty": supress_notation(qty, self.qty_precision)}
                    res = self.bb_request(
                        method="POST",
                        url=self.bb_sell_market_order_url,
                        payload=tp_order,
                    )
            
            # If error pass it up to parent function, can't continue
            if "error" in res:
                raise TraillingProfitError(res["error"])

            deal_schema = DealSchema()
            deal = deal_schema.dump(deal_data)

            msg = f"Completed take profit after failing to break trailling"

            bot = self.db_collection.update_one(
                {"_id": self.active_bot._id},
                {"$set": {"deal": deal, "status": "completed"}},
                {"$push": {"errors": msg}}
            )
        except Exception as error:
            self.update_deal_logs("Failed to close trailling take profit: " + error)
            raise TraillingProfitError(error)

        pass # Completed

    def open_deal(self):

        """
        Mandatory deals section
        - If base order deal is not executed, bot is not activated
        """
        # If there is already a base order do not execute
        base_order_deal = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if len(bo_deal) > 0 and (bo_deal["deal_type"] == "base_order")
            ),
            None,
        )

        if not base_order_deal:
            bot = self.base_order()
        else:
            bot = self.db_collection.find_one({"_id": self.active_bot._id})

        """
        Optional deals section
        """
        deal_data = self.active_bot.deal

        # Below take profit order goes first, because stream does not return a value
        # If there is already a take profit do not execute
        # If there is no base order can't execute
        check_bo = False
        check_tp = True
        if hasattr(bot, "orders") and len(bot.orders) > 0:
            for order in bot.orders:
                if len(order) > 0 and (order["deal_type"] == "base_order"):
                    check_bo = True
                if len(order) > 0 and order["deal_type"] == "take_profit":
                    check_tp = False

        if check_bo and check_tp:
            if bot.trailling == "true":
                bot = self.trailling_profit(deal_data)
            else:
                bot = self.take_profit_order(deal_data)

        # Update stop loss regarless of base order
        if hasattr(bot, "stop_loss") and float(bot.stop_loss) > 0:
            buy_price = float(bot.deal.buy_price)
            stop_loss_price = buy_price - (buy_price * float(bot.stop_loss) / 100)
            deal_data.stop_loss_price = supress_notation(
                stop_loss_price, self.price_precision
            )

        # Keep trailling_stop_loss_price up to date in case of failure to update in autotrade
        if deal_data and deal_data.trailling_stop_loss_price > 0:
        
            take_profit = float(deal_data.trailling_profit) * (
                1 + (float(bot.take_profit) / 100)
            )
            # Update trailling_stop_loss
            deal_data.trailling_stop_loss_price = float(take_profit) - (
                float(take_profit) * (float(bot.trailling_deviation) / 100)
            )

        try:
            deal_schema = DealSchema()
            deal = deal_schema.dump(deal_data)
            self.db_collection.update_one({"_id": self.active_bot._id}, {"$set": {"deal": deal}})

        except ValidationError as error:
            msg = f"Open deal error: {error.messages}"
            raise OpenDealError(msg)
        except AttributeError as error:
            msg = f"Open deal error: {error.messages}"
            raise OpenDealError(msg)
        except Exception as e:
            raise OpenDealError(e)

        pass

    def close_all(self):
        """
        Close all deals and sell pair
        1. Close all deals
        2. Sell Coins
        3. Delete bot
        """
        orders = self.active_bot.orders

        # Close all active orders
        if len(orders) > 0:
            for d in orders:
                if "deal_type" in d and (
                    d["status"] == "NEW" or d["status"] == "PARTIALLY_FILLED"
                ):
                    order_id = d["order_id"]
                    res = requests.delete(
                        url=f"{self.bb_close_order_url}/{self.active_bot.pair}/{order_id}"
                    )

                    if isinstance(handle_error(res), Response):
                        return handle_error(res)

        # Sell everything
        pair = self.active_bot.pair
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


    def update_take_profit(self, order_id):
        """
        Update take profit after websocket order endpoint triggered
        - Close current opened take profit order
        - Create new take profit order
        - Update database by replacing old take profit deal with new take profit deal
        """
        bot = self.active_bot
        if "deal" in bot:
            if bot.deal["order_id"] == order_id:
                so_deal_price = bot.deal["buy_price"]
                # Create new take profit order
                new_tp_price = float(so_deal_price) + (
                    float(so_deal_price) * float(bot.take_profit) / 100
                )
                asset = self.find_baseAsset(bot.pair)

                # First cancel old order to unlock balance
                close_order_params = {"symbol": bot.pair, "orderId": order_id}
                cancel_response = requests.post(
                    url=self.bb_close_order_url, params=close_order_params
                )
                if cancel_response.status_code != 200:
                    print("Take profit order not found, no need to cancel")
                else:
                    print("Old take profit order cancelled")

                qty = round_numbers(self.get_one_balance(asset), self.qty_precision)
                new_tp_order = {
                    "pair": bot.pair,
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
                for d in bot.deals:
                    if d["deal_type"] != "take_profit":
                        new_deals.append(d)

                # Append now new take_profit deal
                new_deals.append(take_profit_order)
                self.active_bot.orders = new_deals
                self.app.db.bots.update_one(
                    {"_id": self.active_bot._id},
                    {
                        "$push": {
                            "orders": take_profit_order,
                            "errors": "take_profit deal successfully updated",
                        }
                    },
                )
                return
        else:
            self.update_deal_logs("Error: Bot does not contain a base order deal")

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

        Not for use when opening new deal
        """
        pair = self.active_bot.pair
        so_qty = self.active_bot.safety_orders[so_index].so_size
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

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(
                order["pair"], order["price"], order["qty"], "BUY"
            )
        else:
            res = self.bb_request(self.bb_buy_order_url, "POST", paylaod=order)

        safety_order = OrderModel(
            timestamp=res["transactTime"],
            order_type=res["type"],
            order_id=res["orderId"],
            pair=res["symbol"],
            deal_type=f"so_{so_index}",
            order_side=res["side"],
            price=res["price"],
            qty=res["origQty"],
            fills=res["fills"],
            status=res["status"],
            time_in_force=res["timeInForce"],
        )

        self.active_bot.orders.append(safety_order)
        new_tp_price = float(safety_order.price) * (
            1 + float(self.active_bot.take_profit) / 100
        )

        # New take profit order
        self.active_bot.deal.take_profit_price = new_tp_price

        commission = 0
        for chunk in safety_order.fills:
            commission += float(chunk["commission"])

        if hasattr(self.active_bot.deal, "buy_total_qty"):
            buy_total_qty = float(self.active_bot.deal.buy_total_qty) + float(
                res["origQty"]
            )
        else:
            buy_total_qty = self.active_bot.base_order_size

        self.active_bot.deal.buy_total_qty = buy_total_qty

        
        order_id = None
        for order in self.active_bot.orders:
            if order["deal_type"] == "take_profit":
                order_id = order["order_id"]
                self.active_bot.orders.remove(order)
                break

        if order_id:
            # First cancel old order to unlock balance
            try:
                self.bb_request(
                    f"{self.bb_close_order_url}/{self.active_bot['pair']}/{order_id}",
                    "DELETE",
                )
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs(f"Take profit order not found, no need to cancel, {error}")
            
            qty = round_numbers(self.active_bot.deal.buy_total_qty, self.qty_precision)
            price = supress_notation(new_tp_price, self.price_precision)
            new_tp_order = {
                "pair": self.active_bot.pair,
                "qty": qty,
                "price": price,
            }
            if self.db_collection.name == "paper_trading":
                tp_order = self.simulate_order(pair, price, qty, "SELL")
            else:
                tp_order = self.bb_request(self.bb_sell_order_url, "POST", payload=new_tp_order)

            take_profit_order = OrderModel(
                timestamp=tp_order["transactTime"],
                deal_type="take_profit",
                order_id=tp_order["orderId"],
                pair=tp_order["symbol"],
                order_side=tp_order["side"],
                order_type=tp_order["type"],
                price=tp_order["price"],
                qty=tp_order["origQty"],
                fills=tp_order["fills"],
                time_in_force=tp_order["timeInForce"],
                status=tp_order["status"],
            )

            self.active_bot.orders.append(take_profit_order)

        try:
            bot_schema = BotSchema()
            bot = bot_schema.dump(self.active_bot)
            bot.pop("_id")

            self.db_collection.update_one(
                {"_id": self.active_bot._id},
                {"$set": bot},
            )
            self.update_deal_logs("Updated Safety orders!")

        except ValidationError as error:
            self.update_deal_logs(f"Safety orders error: {error.messages}")
            return
        except (TypeError, AttributeError) as error:
            message = str(";".join(error.args))
            self.update_deal_logs(f"Safety orders error: {message}")
            return
        except Exception as error:
            self.update_deal_logs(f"Safety orders error: {error}")
            return

        pass

    def execute_stop_loss(self, price):
        """
        Update stop limit after websocket
        - Hard sell (order status="FILLED" immediately) initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot
        """
        bot = self.active_bot
        if self.db_collection.name == "paper_trading":
            qty = bot.deal.buy_total_qty
        else:
            qty = self.compute_qty(bot.pair)
        
        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        if not qty:
            self.update_deal_logs(f"Cannot execute update stop limit, quantity is {qty}. Deleting bot")
            params = {
                "id": self.active_bot._id
            }
            self.bb_request(f"{self.bb_bot_url}", "DELETE", params=params)
            return

        order_id = None
        for order in bot.orders:
            if order.deal_type == "take_profit":
                order_id = order.order_id
                bot.orders.remove(order)
                break

        if order_id:
            try:
                # First cancel old order to unlock balance
                self.bb_request(f"{self.bb_close_order_url}/{self.active_bot.pair}/{order_id}", "DELETE")
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs("Take profit order not found, no need to cancel")
                return


        book_order = Book_Order(bot.pair)
        price = float(book_order.matching_engine(True, qty))
        if not price:
            price = float(book_order.matching_engine(True))

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(bot.pair, price, qty, "SELL")
        else:
            try:
                if price:
                    stop_limit_order = {
                        "pair": bot.pair,
                        "qty": qty,
                        "price": supress_notation(price, self.price_precision),
                    }
                    res = self.bb_request(
                        method="POST", url=self.bb_sell_order_url, payload=stop_limit_order
                    )
                else:
                    stop_limit_order = {"pair": bot.pair, "qty": qty}
                    res = self.bb_request(
                        method="POST",
                        url=self.bb_sell_market_order_url,
                        payload=stop_limit_order,
                    )
            except QuantityTooLow as error:
                # Delete incorrectly activated or old bots
                result = self.bb_request(self.bb_bot_url, "DELETE", params={"id": self.active_bot._id})
                print(f"Deleted obsolete bot {self.active_bot.pair}")
            except Exception as error:
                self.update_deal_logs(f"Error trying to open new stop_limit order {error}")
                return


        if res["status"] == "NEW":
            self.update_deal_logs("Failed to execute stop loss order (status NEW), retrying...")
            self.execute_stop_loss(price)

        stop_loss_order = OrderModel(
            timestamp=res['transactTime'],
            deal_type="stop_loss",
            order_id=res["orderId"],
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res["price"],
            qty=res["origQty"],
            fills=res["fills"],
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        commission = 0
        for chunk in res["fills"]:
            commission += float(chunk["commission"])

        self.active_bot.orders.append(stop_loss_order)
        self.active_bot.status = "completed"

        try:

            bot_schema = BotSchema()
            bot = bot_schema.dump(self.active_bot)
            bot.pop("_id")

            self.db_collection.update_one(
                {"_id": self.active_bot._id},
                {"$set": bot},
            )
        except ValidationError as error:
            self.update_deal_logs(f"Stop loss error: {error.messages}")
            return
        except (TypeError, AttributeError) as error:
            message = str(";".join(error.args))
            self.update_deal_logs(f"Stop loss error: {message}")
            return
        except Exception as error:
            self.update_deal_logs(f"Stop loss error: {error}")
            return
        pass


