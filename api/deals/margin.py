import os
from time import time

from binance.client import Client
from deals.base import BaseDeal
from deals.models import BinanceRepayRecords
from deals.schema import DealSchema, MarginOrderSchema
from orders.models.book_order import Book_Order
from pymongo import ReturnDocument
from tools.handle_error import encode_json


class MarginShortError(Exception):
    pass


class MarginDeal(BaseDeal):
    def __init__(self) -> None:
        # Inherit from parent class
        self.client = Client(os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"])

    def simulate_margin_order(self, qty, side):
        book_order = Book_Order(self.active_bot.pair)
        price = float(book_order.matching_engine(True, qty))
        order = {
            "symbol": self.active_bot.pair,
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
            "marginBuyBorrowAmount": 5,
            "marginBuyBorrowAsset": "BTC",
            "fills": [],
        }
        return order

    def buy_order(self, price, qty):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """
        book_order = Book_Order(self.active_bot.pair)
        price = float(book_order.matching_engine(True, qty))
        response = self.client.create_margin_order(
            symbol=self.active_bot.pair,
            side="BUY",
            type="LIMIT",
            timeInForce="GTC",
            quantity=qty,
            price=price,
            isIsolated="TRUE",
        )

        return response

    def sell_order(self, qty):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """
        book_order = Book_Order(self.active_bot.pair)
        price = float(book_order.matching_engine(False, qty))
        response = self.client.create_margin_order(
            symbol=self.active_bot.pair,
            side="SELL",
            type="LIMIT",
            timeInForce="GTC",
            quantity=qty,
            price=price,
            isIsolated="TRUE",
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
            raise MarginShortError("No funds in Cross Margin account")
        return assets

    def get_loan_record(self):
        """
        Get loan details
        https://binance-docs.github.io/apidocs/spot/en/#query-loan-record-user_data
        """
        asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
        transaction = self.client.repay_margin_loan(asset=asset, amount="1.1")

        pass

    def get_isolated_balance(self):
        """
        Get balance of Isolated Margin account

        Use isolated margin account is preferrable,
        because this is the one that supports the most assets
        """
        info = self.client.get_isolated_margin_account()
        assets = info["assets"]
        if len(assets) == 0:
            raise MarginShortError("No funds in Isolated Margin account")
        return assets

    def init_margin_short(self, borrow_rate=2.5):
        """
        Pre-tasks for db_collection = bots
        These tasks are not necessary for paper_trading

        1. transfer funds
        2. create loan
        3. borrow 2.5x to do base order
        """
        print("Initializating margin_short tasks for real bots trading")
        # Check margin account balance first
        balance = self.get_isolated_balance()
        find_balance_to_use = next(
            (
                item
                for item in balance
                if item["asset"] == self.active_bot.balance_to_use
            ),
            None,
        )
        if not find_balance_to_use:
            # transfer
            transfer_transaction = self.client.transfer_spot_to_isolated_margin(
                asset=self.active_bot.balance_to_use,
                symbol=self.active_bot.pair,
                amount=self.active_bot.base_order_size,
            )
            if not transfer_transaction:
                raise MarginShortError(
                    f"Not enough {self.active_bot.balance_to_use} in Isolated Margin account to execute base_order"
                )
            else:
                asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
                # In the future, amount_to_borrow = base + base * (2.5)
                amount_to_borrow = self.active_bot.base_order_size
                margin_loan_transaction = self.client.create_margin_loan(
                    asset=asset, amount=amount_to_borrow, isIsolated=True
                )
                if margin_loan_transaction:
                    self.active_bot.deal.buy_total_qty = amount_to_borrow
                    self.active_bot.deal.margin_loan_id = margin_loan_transaction

                    return

                else:
                    raise MarginShortError(margin_loan_transaction)

        pass

    def terminate_margin_short(self):
        """

        1. buy back
        2. repay loan
        2. transfer back to spot
        """
        print("Terminating margin_short tasks for real bots trading")
        # Check margin account balance first
        balance = self.get_isolated_balance()
        find_balance_to_use = next(
            (
                item
                for item in balance
                if item["asset"] == self.active_bot.balance_to_use
            ),
            None,
        )
        if find_balance_to_use:
            # repay
            asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
            amount = (
                self.active_bot.deal.buy_total_qty
                if self.active_bot.deal.buy_total_qty
                else self.active_bot.base_order_size
            )
            repay_transaction = self.client.repay_margin_loan(
                asset=asset, amount=amount
            )
            if repay_transaction:
                repay_details: BinanceRepayRecords = (
                    self.client.get_margin_repay_details(
                        isolatedSymbol=self.active_bot.pair
                    )
                )
                self.active_bot.deal.margin_short_loan_interest = repay_details[
                    "interest"
                ]
                self.active_bot.deal.margin_short_loan_principal = repay_details[
                    "principal"
                ]
                self.active_bot.deal.margin_short_loan_timestamp = repay_details[
                    "timestamp"
                ]
                self.active_bot.status = "completed"

                transfer_transaction = self.client.transfer_isolated_margin_to_spot(
                    asset=asset, symbol=self.active_bot.pair, amount=amount
                )

                if transfer_transaction:
                    self.active_bot.deal.buy_total_qty = amount_to_borrow
                    completion_msg = f"Margin_short bot repaid, funds transferred back to SPOT. Bot completed"
                    self.active_bot.errors.append(completion_msg)
                    print(completion_msg)
                else:
                    raise MarginShortError(
                        f"Unable to terminate margin_short transfer transaction: {transfer_transaction}"
                    )

            else:
                raise MarginShortError(
                    f"Unable to repay transaction: {repay_transaction}"
                )

            if not transfer_transaction:
                raise MarginShortError(
                    f"Not enough {self.active_bot.balance_to_use} in Isolated Margin account to execute base_order"
                )
            else:

                # In the future, amount_to_borrow = base + base * (2.5)
                amount_to_borrow = self.active_bot.base_order_size
                margin_loan_transaction = self.client.create_margin_loan(
                    asset=asset, amount=amount_to_borrow, isIsolated=True
                )
                if margin_loan_transaction:
                    self.active_bot.deal.buy_total_qty = amount_to_borrow
                    self.active_bot.deal.margin_loan_id = margin_loan_transaction

                    # Activate bot
                    self.active_bot.status = "completed"

                    bot = encode_json(self.active_bot)
                    if "_id" in bot:
                        bot.pop("_id")  # _id is what causes conflict not id

                    document = self.db_collection.find_one_and_update(
                        {"id": self.active_bot.id},
                        {"$set": bot},
                        return_document=ReturnDocument.AFTER,
                    )

                    return document

                else:
                    raise MarginShortError(margin_loan_transaction)
        else:
            raise MarginShortError(
                f"No margin found when trying to terminate {self.active_bot.pair}"
            )

    def margin_short_base_order(self):
        """
        Same functionality as usual base_order
        with a few more fields. This is used during open_deal

        1. Check margin account balance
        2. Carry on with usual base_order
        """
        print(f"Opening margin margin_long_base_order")
        # Uncomment for production
        if self.db_collection == "bots":
            self.init_margin_short()
            # Margin sell
            order_res = self.sell_order(self.active_bot.deal.buy_total_qty)
        else:
            # Margin sell
            order_res = self.simulate_margin_order(
                self.active_bot.deal.buy_total_qty, "SELL"
            )

        order_data = MarginOrderSchema(
            timestamp=order_res["transactTime"],
            order_id=order_res["orderId"],
            deal_type="margin_short",
            pair=order_res["symbol"],
            order_side=order_res["side"],
            order_type=order_res["type"],
            price=order_res["price"],
            qty=order_res["origQty"],
            fills=order_res["fills"],
            time_in_force=order_res["timeInForce"],
            status=order_res["status"],
        )

        self.active_bot.orders.append(order_data)
        tp_price = float(order_res["price"]) * 1 + (
            float(self.active_bot.take_profit) / 100
        )

        self.active_bot.deal = DealSchema(
            margin_short_sell_timestamp=order_res["transactTime"],
            margin_short_sell_price=order_res["price"],
            buy_total_qty=order_res["origQty"],
            margin_short_base_order=order_res["origQty"],
            margin_short_take_profit_price=tp_price,
        )

        # Activate bot
        self.active_bot.status = "active"

        bot = encode_json(self.active_bot)
        if "_id" in bot:
            bot.pop("_id")  # _id is what causes conflict not id

        document = self.db_collection.find_one_and_update(
            {"id": self.active_bot.id},
            {"$set": bot},
            return_document=ReturnDocument.AFTER,
        )

        return document

    def streaming_updates(self, close_price: str):
        """
        Margin_short streaming updates
        """

        price = float(close_price)
        self.active_bot.deal.current_price = price

        # Direction 1: upward trend
        # Future feature: trailling
        if price < self.active_bot.deal.take_profit_price:
            self.terminate_margin_short()
        
        # Direction 2: downard trend
        else:
            self.margin_short_stop_loss()

    def margin_short_stop_loss(self):
        """
        Triggers stop_loss for margin_short
        this is used during streaming updates
        """
        price = self.active_bot.deal.buy_price

        if (
            hasattr(self.active_bot, "stop_loss")
            and float(self.active_bot.stop_loss) > 0
        ):
            stop_loss_price = price - (price * (float(self.active_bot.stop_loss) / 100))
            self.active_bot.deal.margin_short_stop_loss_price = stop_loss_price
