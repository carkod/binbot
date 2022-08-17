from decimal import Decimal
from time import time

from api.account.account import Account
from api.app import create_app
from api.orders.models.book_order import Book_Order
from api.tools.handle_error import bot_errors
from api.tools.round_numbers import round_numbers, supress_notation
from bson.objectid import ObjectId


class TestDealUpdates(Account):
    """
    An almost duplicate of Deal class, created to avoid circular and maximum depth issues
    It has some more additional methods and data for the purpose of websocket updating bots
    """

    def __init__(self, bot):

        self.active_bot = bot
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
        id = str(ObjectId())
        self.response_order = {
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

    def _compute_qty(self, pair):
        """
        Helper function to compute buy_price.
        Previous qty = bot["deal"]["buy_total_qty"]
        """

        asset = self.find_baseAsset(pair)
        balance = self.get_one_balance(asset)
        if not balance:
            return None
        qty = round_numbers(balance, self.qty_precision)
        return qty

    def get_one_balance(self, symbol="BTC"):
        # Response after request
        data = self.bb_request(url=self.bb_balance_url)
        symbol_balance = next(
            (x["free"] for x in data["data"] if x["asset"] == symbol), None
        )
        return symbol_balance
    
    def simulate_order(self, pair, price, qty, side):
        self.response_order["symbol"] = pair
        self.response_order["price"] = price
        if qty:
            self.response_order["origQty"] = qty
        self.response_order["executedQty"] = qty
        self.response_order["cummulativeQuoteQty"] = qty
        self.response_order["side"] = side
        return self.response_order

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

                qty = round_numbers(self.get_one_balance(asset), self.qty_precision)
                price = supress_notation(new_tp_price, self.price_precision)
                order = self.simulate_order(bot["pair"], price, qty, "SELL")

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
                self.app.db.paper_trading.update_one(
                    {"_id": self.active_bot["_id"]},
                    {
                        "$push": {
                            "orders": take_profit_order,
                            "errors": "take_profit deal successfully updated",
                        }
                    },
                )
                return

    def execute_stop_loss(self, price):
        """
        Update stop limit after websocket
        - Hard sell (order status="FILLED" immediately) initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot
        """
        bot = self.active_bot
        qty = bot["deal"]["buy_total_qty"]

        book_order = Book_Order(bot["pair"])
        price = float(book_order.matching_engine(True, qty))
        if not price:
            price = float(book_order.matching_engine(True))

        for order in bot["orders"]:
            if order["deal_type"] == "take_profit":
                bot["orders"].remove(order)
                break

        price = supress_notation(price, self.price_precision)
        res = self.simulate_order(bot["pair"], price, qty, "SELL")

        if res["status"] == "NEW":
            bot_errors("Failed to execute order (status NEW), retrying...", bot, status="completed")
            self.execute_stop_loss(price)

        # Append now stop_limit deal
        stop_limit_response = {
            "deal_type": "stop_loss",
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

        self.active_bot["orders"].append(stop_limit_response)
        try:
            self.app.db.paper_trading.update_one(
                {"_id": bot["_id"]},
                {
                    "$push": {"orders": stop_limit_response},
                    "$set": {"deal.sell_timestamp": res["transactTime"], "status": "completed"},
                },
            )
        except Exception as error:
            print(error)
        pass

    def trailling_stop_loss(self, price):
        """
        Update stop limit after websocket
        - Hard Sell initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot
        """
        bot = self.active_bot
        qty = bot["deal"]["buy_total_qty"]
        book_order = Book_Order(bot["pair"])
        
        # In the case of test bots, qty is not real, so there always will be prices
        price = float(book_order.matching_engine(True, qty))
        if not price:
            price = float(book_order.matching_engine(True))

        price = supress_notation(price, self.price_precision)
        res = self.simulate_order(bot["pair"], price, qty, "SELL")

        # Append now stop_loss deal
        trailling_stop_loss_response = {
            "deal_type": "trailling_stop_loss",
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
        self.app.db.paper_trading.update_one(
            {"_id": bot["_id"]},
            {
                "$set": {
                    "status": "completed",
                    "deal.take_profit_price": res["price"],
                    "orders": bot["orders"],
                    "deal.sell_timestamp": res["transactTime"],
                },
            },
        )
        print("Bot completed", bot["pair"])
        return "completed"
