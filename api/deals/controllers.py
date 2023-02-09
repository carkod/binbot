import numpy
import requests
from pymongo import ReturnDocument
from requests.exceptions import HTTPError
from pydantic import ValidationError

from deals.base import BaseDeal
from deals.margin import MarginDeal
from bots.schemas import BotSchema
from deals.models import DealModel, BinanceOrderModel
from deals.schema import DealSchema, OrderSchema
from orders.models.book_order import Book_Order
from tools.exceptions import (
    OpenDealError,
    ShortStrategyError,
    TakeProfitError,
    TraillingProfitError,
)
from tools.handle_error import NotEnoughFunds, QuantityTooLow, handle_binance_errors, encode_json
from tools.round_numbers import round_numbers, supress_notation

class CreateDealController(BaseDeal):
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
        super().__init__(bot, db_collection)
        # Inherit from parent class
        

    def get_one_balance(self, symbol="BTC"):
        # Response after request
        print(self.bb_balance_url)
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


    def base_order(self):
        """
        Required initial order to trigger bot.
        Other orders require this to execute,
        therefore should fail if not successful

        1. Initial base purchase
        2. Set take_profit
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

        # setup stop_loss_price
        stop_loss_price = 0
        if (
            hasattr(self.active_bot, "stop_loss")
            and float(self.active_bot.stop_loss) > 0
        ):
            stop_loss_price = price - (price * (float(self.active_bot.stop_loss) / 100))

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

        order_data = OrderSchema(
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

        self.active_bot.deal = DealSchema(
            buy_timestamp=res["transactTime"],
            buy_price=res["price"],
            buy_total_qty=res["origQty"],
            current_price=res["price"],
            take_profit_price=tp_price,
            stop_loss_price=stop_loss_price,
        )

        # Activate bot
        self.active_bot.status = "active"

        bot = encode_json(self.active_bot)
        if "_id" in bot:
            bot.pop("_id") # _id is what causes conflict not id

        document = self.db_collection.find_one_and_update(
            {"id": self.active_bot.id},
            {"$set": bot},
            return_document=ReturnDocument.AFTER,
        )

        return document

    def take_profit_order(self) -> BotSchema:
        """
        take profit order (Binance take_profit)
        - We only have stop_price, because there are no book bids/asks in t0
        - take_profit order can ONLY be executed once base order is filled (on Binance)
        """

        deal_buy_price = self.active_bot.buy_price
        buy_total_qty = self.active_bot.buy_total_qty
        price = (1 + (float(self.active_bot.take_profit) / 100)) * float(deal_buy_price)

        if self.db_collection.name == "paper_trading":
            qty = self.active_bot.deal.buy_total_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)

        qty = supress_notation(buy_total_qty, self.qty_precision)
        price = supress_notation(price, self.price_precision)

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(self.active_bot.pair, price, qty, "SELL")
            if price:
                res = self.simulate_order(
                    self.active_bot.pair,
                    price,
                    qty,
                    "SELL",
                )
            else:
                price = (1 + (float(self.active_bot.take_profit) / 100)) * float(deal_buy_price)
                res = self.simulate_order(
                    self.active_bot.pair,
                    price,
                    qty,
                    "SELL",
                )
        else:
            tp_order = {
                "pair": self.active_bot.pair,
                "qty": supress_notation(qty, self.qty_precision),
                "price": supress_notation(price, self.price_precision),
            }
            res = self.bb_request(
                method="POST", url=self.bb_sell_order_url, payload=tp_order
            )

        # If error pass it up to parent function, can't continue
        if "error" in res:
            raise TakeProfitError(res["error"])

        order_data = BinanceOrderModel(
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
        self.active_bot.deal.sell_price = res["price"]
        self.active_bot.deal.sell_qty = res["origQty"]
        self.active_bot.deal.sell_timestamp = res["transactTime"]
        self.active_bot.status = "completed"
        msg = f"Completed take profit"
        self.active_bot.errors.append(msg)

        try:
            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            bot = self.db_collection.find_one_and_update(
                {"id": self.active_bot.id},
                {
                    "$set": bot,
                },
                return_document=ReturnDocument.AFTER,
            )
        except Exception as error:
            raise TakeProfitError(error)

        return bot

    def trailling_profit(self) -> BotSchema:
        """
        Sell at take_profit price, because prices will not reach trailling
        """

        deal_data = self.active_bot.deal
        deal_buy_price = self.active_bot.deal.buy_price
        price = (1 + (float(self.active_bot.take_profit) / 100)) * float(deal_buy_price)

        if self.db_collection.name == "paper_trading":
            qty = deal_data.buy_total_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)
            # Already sold?
            if not qty:
                print(f"Bot already closed? There is no {self.active_bot.pair} quantity in the balance. Please delete the bot.")

        # Dispatch fake order
        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(
                self.active_bot.pair,
                price,
                qty,
                "SELL",
            )

        # Dispatch real order
        else:

            tp_order = {
                "pair": self.active_bot.pair,
                "qty": supress_notation(qty, self.qty_precision),
                "price": supress_notation(price, self.price_precision),
            }

            res = self.bb_request(
                method="POST", url=self.bb_sell_order_url, payload=tp_order
            )

        # If error pass it up to parent function, can't continue
        if "error" in res:
            raise TraillingProfitError(res["error"])

        order_data = BinanceOrderModel(
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
        self.active_bot.deal.trailling_profit_price = res["price"]
        self.active_bot.deal.sell_price = res["price"]
        self.active_bot.deal.sell_qty = res["origQty"]
        self.active_bot.deal.sell_timestamp = res["transactTime"]
        self.active_bot.status = "completed"
        msg = f"Completed take profit after failing to break trailling {self.active_bot.pair}"
        self.active_bot.errors.append(msg)
        print(msg)

        try:

            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            bot = self.db_collection.find_one_and_update(
                {"id": self.active_bot.id},
                {
                    "$set": bot,
                },
                return_document=ReturnDocument.AFTER,
            )

        except Exception as error:
            self.update_deal_logs(f"Failed to close trailling take profit: {error}")
            raise TraillingProfitError(error)

        return bot

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

                    handle_binance_errors(res)

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

                # New take profit order successfully created
                order = handle_binance_errors(res)

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
                self.db.bots.update_one(
                    {"id": self.active_bot.id},
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
        - Cancel old take profit order to unlock balance
        - Create new so
        - Deactivate so
        - Update DB with new deal data
        - Create new take profit order
        - Update DB with new take profit deal data

        Not for use when opening new deal
        """
        pair = self.active_bot.pair
        so_qty = self.active_bot.safety_orders[so_index].so_size
        book_order = Book_Order(pair)
        price = book_order.matching_engine(False, so_qty)
        qty = round_numbers(
            float(so_qty),
            self.qty_precision,
        )
        order = {
            "pair": pair,
            "qty": supress_notation(qty, self.qty_precision),
            "price": supress_notation(price, self.price_precision),
        }

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(pair, price, qty, "BUY")
        else:
            try:
                res = self.bb_request(self.bb_buy_order_url, "POST", payload=order)
            except NotEnoughFunds as error:
                # If there are no funds to execute SO, this needs to be done manually then
                # Deactivate SO to avoid it triggering constantly
                # Send error message to the bot logs
                self.active_bot.safety_orders[so_index].status = 2
                self.active_bot.errors.append("Not enough funds to execute SO")
                
                bot = encode_json(self.active_bot)
                if "_id" in bot:
                    bot.pop("_id")

                self.db_collection.update_one(
                    {"id": self.active_bot.id},
                    {"$set": bot},
                )
                return

        safety_order = BinanceOrderModel(
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
        self.active_bot.safety_orders[so_index].status = 1
        self.active_bot.safety_orders[so_index].order_id = res["orderId"]
        self.active_bot.safety_orders[so_index].buy_timestamp = res["transactTime"]
        self.active_bot.safety_orders[so_index].so_size = res[
            "origQty"
        ]  # update with actual quantity

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

        # weighted average buy price
        # first store the previous price for the record
        self.active_bot.deal.original_buy_price = self.active_bot.deal.buy_price
        if self.active_bot.orders and len(self.active_bot.orders) > 0:
            weighted_avg_buy_price = 0
            for order in self.active_bot.orders:
                if order.deal_type == "base_order":
                    weighted_avg_buy_price += float(order.qty) * float(order.price)
                if order.deal_type.startswith("so"):
                    weighted_avg_buy_price += float(order.qty) * float(order.price)

        self.active_bot.deal.buy_price = weighted_avg_buy_price / buy_total_qty

        order_id = None
        for order in self.active_bot.orders:
            if order.deal_type == "take_profit":
                order_id = order.order_id
                self.active_bot.orders.remove(order)
                break

        if order_id and self.db_collection.name != "paper_trading":
            # First cancel old order to unlock balance
            try:
                self.bb_request(
                    f"{self.bb_close_order_url}/{self.active_bot.pair}/{order_id}",
                    "DELETE",
                )
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs(
                    f"Take profit order not found, no need to cancel, {error}"
                )

        # Because buy_price = avg_buy_price after so executed
        # we can use this to update take_profit_price
        new_tp_price = float(self.active_bot.deal.buy_price) * (
            1 + float(self.active_bot.take_profit) / 100
        )

        # Reset deal take_profit and trailling (even if there is no trailling, setting it 0 would be equal to cancelling)
        self.active_bot.deal.take_profit_price = new_tp_price
        self.active_bot.deal.trailling_stop_loss_price = 0

        try:
            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            self.db_collection.update_one(
                {"id": self.active_bot.id},
                {"$set": bot},
            )
            self.update_deal_logs("Safety order triggered!")
            print("Safety order triggered!")

        except ValidationError as error:
            self.update_deal_logs(f"Safety orders error: {error}")
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
        if self.db_collection.name == "paper_trading":
            qty = self.active_bot.deal.buy_total_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)

        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        if not qty:
            self.update_deal_logs(
                f"Cannot execute update stop limit, quantity is {qty}. Deleting bot"
            )
            params = {"id": self.active_bot.id}
            self.bb_request(f"{self.bb_bot_url}", "DELETE", params=params)
            return

        order_id = None
        for order in self.active_bot.orders:
            if order.deal_type == "take_profit":
                order_id = order.order_id
                self.active_bot.orders.remove(order)
                break

        if order_id:
            try:
                # First cancel old order to unlock balance
                self.bb_request(
                    f"{self.bb_close_order_url}/{self.active_bot.pair}/{order_id}",
                    "DELETE",
                )
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs("Take profit order not found, no need to cancel")
                return

        book_order = Book_Order(self.active_bot.pair)
        price = float(book_order.matching_engine(True, qty))
        if not price:
            price = float(book_order.matching_engine(True))

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(self.active_bot.pair, price, qty, "SELL")
        else:
            try:
                stop_limit_order = {
                    "pair": self.active_bot.pair,
                    "qty": qty,
                    "price": supress_notation(price, self.price_precision),
                }
                res = self.bb_request(
                    method="POST",
                    url=self.bb_sell_order_url,
                    payload=stop_limit_order,
                )
            except QuantityTooLow as error:
                # Delete incorrectly activated or old bots
                self.bb_request(f"{self.bb_bot_url}/{self.active_bot.id}", "DELETE")
                print(f"Deleted obsolete bot {self.active_bot.pair}")
            except Exception as error:
                self.update_deal_logs(
                    f"Error trying to open new stop_limit order {error}"
                )
                return

        if res["status"] == "NEW":
            self.update_deal_logs(
                "Failed to execute stop loss order (status NEW), retrying..."
            )
            self.execute_stop_loss(price)

        stop_loss_order = BinanceOrderModel(
            timestamp=res["transactTime"],
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
        self.active_bot.deal.sell_price = res["price"]
        self.active_bot.deal.sell_qty = res["origQty"]
        self.active_bot.deal.sell_timestamp = res["transactTime"]
        msg = f"Completed Stop loss"
        self.active_bot.errors.append(msg)
        self.active_bot.status = "completed"

        try:

            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            self.db_collection.update_one(
                {"id": self.active_bot.id},
                {"$set": bot},
            )

        except ValidationError as error:
            self.update_deal_logs(f"Stop loss error: {error}")
            return
        except (TypeError, AttributeError) as error:
            message = str(";".join(error.args))
            self.update_deal_logs(f"Stop loss error: {message}")
            return
        except Exception as error:
            self.update_deal_logs(f"Stop loss error: {error}")
            return
        pass

    def execute_short_sell(self):
        """
        Short strategy sell. Similar to stop loss, but it will keep tracking the price until it short_buys
        - Hard sell (order status="FILLED" immediately) initial amount crypto in deal
        - Close current opened take profit order
        - Remove old base_order and reset deal for future open_deal
        - Switch strategy to short
        - Wait for short_sell_price to hit
        """
        bot = self.active_bot
        if self.db_collection.name == "paper_trading":
            qty = bot.deal.buy_total_qty
        else:
            qty = self.compute_qty(bot.pair)

        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        if not qty:
            self.update_deal_logs(
                f"Cannot execute short sell, quantity is {qty}. Deleting bot"
            )
            params = {"id": str(self.active_bot.id)}
            self.bb_request(f"{self.bb_bot_url}", "DELETE", params=params)
            return

        order_id = None
        for order in bot.orders:
            # With short_sell, Take profit changes and base_order needs to be removed to execute base_order
            if order.deal_type == "take_profit" or order.deal_type == "base_order":
                order_id = order.order_id
                bot.orders.remove(order)
                break

        if order_id:
            try:
                # First cancel old order to unlock balance
                self.bb_request(
                    f"{self.bb_close_order_url}/{self.active_bot.pair}/{order_id}",
                    "DELETE",
                )
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs("Take profit order not found, no need to cancel")
                pass

        book_order = Book_Order(bot.pair)
        price = float(book_order.matching_engine(True, qty))
        if not price:
            price = float(book_order.matching_engine(True))

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(bot.pair, price, qty, "SELL")
        else:
            try:
                if price:
                    short_sell_order_payload = {
                        "pair": bot.pair,
                        "qty": qty,
                        "price": supress_notation(price, self.price_precision),
                    }
                    res = self.bb_request(
                        method="POST",
                        url=self.bb_sell_order_url,
                        payload=short_sell_order_payload,
                    )
                else:
                    short_sell_order_payload = {"pair": bot.pair, "qty": qty}
                    res = self.bb_request(
                        method="POST",
                        url=self.bb_sell_market_order_url,
                        payload=short_sell_order_payload,
                    )
            except QuantityTooLow as error:
                # Delete incorrectly activated or old bots
                self.bb_request(
                    self.bb_bot_url, "DELETE", params={"id": str(self.active_bot.id)}
                )
                print(f"Deleted obsolete bot {self.active_bot.pair}")
            except Exception as error:
                self.update_deal_logs(
                    f"Error trying to open new short_sell order {error}"
                )
                return

        if res["status"] == "NEW":
            self.update_deal_logs(
                "Failed to execute stop loss order (status NEW), retrying..."
            )
            self.execute_short_sell()

        short_sell_order = BinanceOrderModel(
            timestamp=res["transactTime"],
            deal_type="short_sell",
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

        self.active_bot.orders.append(short_sell_order)
        self.active_bot.short_sell_price = 0  # stops short_sell position
        self.active_bot.strategy = "short"
        self.active_bot.deal.short_sell_price = res["price"]
        self.active_bot.deal.short_sell_qty = res["origQty"]
        self.active_bot.deal.short_sell_timestamp = res["transactTime"]
        # reset trailling_stop_loss_price after short is triggered
        self.active_bot.deal.trailling_stop_loss_price = 0
        self.active_bot.deal.take_profit_price = float(
            self.active_bot.deal.buy_price
        ) * (1 + (float(self.active_bot.take_profit) / 100))

        # Reset deal to allow new open_deal to populate
        new_deal = DealModel()
        self.active_bot.deal = new_deal

        msg = f"Completed Short sell position"
        self.active_bot.errors.append(msg)

        try:

            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            self.db_collection.update_one(
                {"id": self.active_bot.id},
                {"$set": bot},
            )
        except ValidationError as error:
            self.update_deal_logs(f"Short sell error: {error}")
            return
        except (TypeError, AttributeError) as error:
            message = str(";".join(error.args))
            self.update_deal_logs(f"Short sell error: {message}")
            return
        except Exception as error:
            self.update_deal_logs(f"Short sell error: {error}")
            return
        pass

    def execute_short_buy(self):
        """
        Short strategy, buy after hitting a certain short_buy_price

        1. Set parameters for short_buy
        2. Open new deal as usual
        """
        self.active_bot.short_buy_price = 0
        self.active_bot.strategy = "long"

        try:
            self.open_deal()
            self.update_deal_logs("Successfully activated bot!")

            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            self.db_collection.update_one(
                {"id": self.active_bot.id},
                {"$set": bot},
            )

        except ValidationError as error:
            self.update_deal_logs(f"Short buy error: {error}")
            return
        except (TypeError, AttributeError) as error:
            message = str(";".join(error.args))
            self.update_deal_logs(f"Short buy error: {message}")
            return
        except OpenDealError as error:
            message = str(";".join(error.args))
            self.update_deal_logs(f"Short buy error: {message}")
        except NotEnoughFunds as e:
            message = str(";".join(e.args))
            self.update_deal_logs(f"Short buy error: {message}")
        except Exception as error:
            self.update_deal_logs(f"Short buy error: {error}")
            return
        return

    def dynamic_take_profit(self, symbol, current_bot, close_price):

        params = {
            "symbol": symbol,
            "interval": current_bot["candlestick_interval"],
        }
        res = requests.get(url=self.bb_candlestick_url, params=params)
        data = handle_binance_errors(res)
        list_prices = numpy.array(data["trace"][0]["close"])
        series_sd = numpy.std(list_prices.astype(numpy.single))
        sd = series_sd / float(close_price)

        print(f"dynamic profit for {symbol} sd: ", sd)
        if sd >= 0:
            self.active_bot.deal.sd = sd
            if current_bot["deal"]["trailling_stop_loss_price"] > 0 and float(close_price) > current_bot["deal"]["trailling_stop_loss_price"]:
                # Too little sd and the bot won't trail, instead it'll sell immediately
                # Too much sd and the bot will never sell and overlap with other positions
                volatility: float = float(sd) / float(close_price)
                if volatility < 0.018:
                    volatility = 0.018
                elif volatility > 0.088:
                    volatility = 0.088

                # sd is multiplied by 2 to increase the difference between take_profit and trailling_stop_loss
                # this avoids closing too early
                new_trailling_stop_loss_price = float(close_price) - (
                    float(close_price) * volatility
                )
                if new_trailling_stop_loss_price > float(
                    self.active_bot.deal.buy_price
                ):
                    self.active_bot.trailling_deviation = volatility
                    self.active_bot.deal.trailling_stop_loss_price = float(close_price) - (float(close_price) * volatility)
                    # Update tralling_profit price
                    self.active_bot.deal.take_profit_price = volatility
                    print(f"Updated trailling_deviation and take_profit {self.active_bot.deal.trailling_stop_loss_price}")

        bot = encode_json(self.active_bot)
        return bot

    def open_deal(self):

        """
        Mandatory deals section
        - If base order deal is not executed, bot is not activated
        """
        # Short strategy checks
        if self.active_bot.strategy == "short":
            if (
                not hasattr(self.active_bot, "short_buy_price")
                or float(self.active_bot.short_buy_price) == 0
            ):
                raise ShortStrategyError(
                    "Short strategy requires short_buy_price to be set, or it will never trigger"
                )
            else:
                pass

        # If there is already a base order do not execute
        base_order_deal = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == "base_order"
            ),
            None,
        )

        if not base_order_deal:
            if self.active_bot.strategy == "margin_short":
                bot = MarginDeal(bot=self.active_bot, db_collection=self.db_collection.name).margin_short_base_order()
            else:
                bot = self.base_order()
            
        else:
            bot = self.db_collection.find_one({"id": self.active_bot.id})
            self.active_bot = BotSchema.parse_obj(bot)

        """
        Optional deals section

        The following functionality is triggered according to the options set in the bot
        """

        # Update stop loss regarless of base order
        if hasattr(self.active_bot, "stop_loss") and float(self.active_bot.stop_loss) > 0:
            if self.active_bot.strategy == "margin_short":
                bot = MarginDeal(bot=self.active_bot, db_collection=self.db_collection).set_margin_short_stop_loss()

            buy_price = float(self.active_bot.deal.buy_price)
            stop_loss_price = buy_price - (buy_price * float(self.active_bot.stop_loss) / 100)
            self.active_bot.deal.stop_loss_price = supress_notation(
                stop_loss_price, self.price_precision
            )

        # Keep trailling_stop_loss_price up to date in case of failure to update in autotrade
        # if we don't do this, the trailling stop loss will trigger
        if self.active_bot.deal and (
            self.active_bot.deal.trailling_stop_loss_price > 0
            or self.active_bot.deal.trailling_stop_loss_price < self.active_bot.deal.buy_price
        ) and not self.active_bot.strategy == "margin_short":

            take_profit_price = float(self.active_bot.deal.buy_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price
            # Update trailling_stop_loss
            # an update of the
            self.active_bot.deal.trailling_stop_loss_price = 0


        self.active_bot.status = "active"
        bot = encode_json(self.active_bot)
        if "_id" in bot:
            bot.pop("_id")

        self.db_collection.update_one({"id": self.active_bot.id}, {"$set": bot})
        return
