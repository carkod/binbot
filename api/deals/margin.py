import os
from time import time

from binance.client import Client
from pymongo import ReturnDocument
from deals.schema import DealSchema, MarginOrderSchema
from orders.models.book_order import Book_Order

from tools.handle_error import encode_json
from tools.round_numbers import round_numbers, supress_notation

class NotEnoughMarginFunds(Exception):
    # Not enough funds in Isolated Margin account
    pass

class MarginDeal:
    def __init__(self, deal_controller) -> None:
        # Inherit from parent class
        self.client = Client(os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"])
        self.deal_controller = deal_controller
        self.active_bot = deal_controller.active_bot
        self.db_collection = deal_controller.db_collection
        self.price_precision = deal_controller.price_precision
        self.qty_precision = deal_controller.qty_precision

    def simulate_margin_order(self, pair, price, qty, side):
        order = {
            "symbol": pair,
            "orderId": self.deal_controller.generate_id(),
            "orderListId": -1,
            "clientOrderId": self.deal_controller.generate_id(),
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "marginBuyBorrowAmount": 5,
            "marginBuyBorrowAsset": "BTC",
            "fills": [],
        }
        return order

    def buy_order(self, price, qty):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """

        response = self.client.create_margin_order(
            symbol=self.active_bot.pair,
            side="BUY",
            type="LIMIT",
            timeInForce="GTC",
            quantity=qty,
            price=price
        )

        return response

    def sell_order(self, price, qty):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """

        response = self.client.create_margin_order(
            symbol=self.active_bot.pair,
            side="SELL",
            type="LIMIT",
            timeInForce="GTC",
            quantity=qty,
            price=price
        )

        return response

    def get_margin_balance(self) -> list:
        """
        Get balance of Cross Margin account.

        @Args:
        asset: str

        """
        info = self.client.get_margin_account()
        assets = [item for item in info["userAssets"] if float(item["netAsset"]) > 0]
        if len(assets) == 0:
            raise NotEnoughMarginFunds("No funds in Cross Margin account")
        return assets

    def get_isolated_balance(self):
        """
        Get balance of Isolated Margin account

        Use isolated margin account is preferrable,
        because this is the one that supports the most assets
        """
        info = self.client.get_isolated_margin_account()
        assets = info["assets"]
        if len(assets) == 0:
            raise NotEnoughMarginFunds("No funds in Isolated Margin account")
        return assets


    def margin_long_base_order(self):
        """
        Same functionality as usual base_order
        with a few more fields

        1. Check margin account balance
        2. Carry on with usual base_order
        """
        print(f"Opening margin margin_long_base_order")
        # Uncomment for production
        # if self.db_collection == "bots":
        # Check margin account balance first
        balance = self.get_isolated_balance()
        find_balance_to_use = next((item for item in balance if item["asset"] == self.active_bot.balance_to_use), None)
        if find_balance_to_use:
            raise NotEnoughMarginFunds(f"Not enough {self.active_bot.balance_to_use} in Isolated Margin account to execute base_order")

        # Proceed with usual base_order
        book_order = Book_Order(self.active_bot.pair)
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
            res = self.simulate_margin_order(
                self.active_bot.pair, supress_notation(price, self.price_precision), qty, "BUY"
            )
        else:
            order_price = supress_notation(price, self.price_precision)
            res = self.buy_order(price=order_price, qty=qty)

        order_data = MarginOrderSchema(
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

    def margin_short_base_order(self):
        print(f"Opening margin margin_short_base_order")
        pass
