import os
from time import time

from binance.client import Client
from binance.exceptions import BinanceAPIException
from requests import HTTPError
from tools.handle_error import QuantityTooLow
from tools.round_numbers import round_numbers, supress_notation
from deals.base import BaseDeal
from deals.models import BinanceRepayRecords
from deals.schema import DealSchema, MarginOrderSchema
from pymongo import ReturnDocument
from tools.handle_error import encode_json
from pydantic import ValidationError

class MarginShortError(Exception):
    pass


class MarginDeal(BaseDeal):
    def __init__(self, bot, db_collection: str) -> None:
        # Inherit from parent class
        self.client = Client(os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"])
        return super().__init__(bot, db_collection)

    def simulate_margin_order(self, qty, side):
        price = float(self.matching_engine(self.active_bot.pair, True, qty))
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
            "isIsolated": "true",
            "fills": [],
        }
        return order

    def buy_order(self, price, qty):
        """
        python-binance wrapper function to make it less verbose and less dependant
        """
        price = float(self.matching_engine(self.active_bot.pair, True, qty))
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
        price = float(self.matching_engine(self.active_bot.pair, False, qty))
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
    
    def compute_isolated_qty(self,):
        """
        Same as compute_qty but with isolated margin balance
        """
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
            return None
        qty = round_numbers(find_balance_to_use, self.qty_precision)
        return qty

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
                if item["symbol"] == self.active_bot.pair
            ),
            None,
        )
        if not find_balance_to_use:
            # transfer
            try:
                self.client.transfer_spot_to_isolated_margin(
                    asset=self.active_bot.balance_to_use,
                    symbol=self.active_bot.pair,
                    amount=self.active_bot.base_order_size,
                )
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
            except BinanceAPIException as error:
                raise MarginShortError(error.message)

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
                if item["symbol"] == self.active_bot.pair
            ),
            None,
        )
        if find_balance_to_use:
            # repay
            try:
                asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
                amount = (
                    self.active_bot.deal.buy_total_qty
                    if self.active_bot.deal.buy_total_qty
                    else self.active_bot.base_order_size
                )
                self.client.repay_margin_loan(
                    asset=asset, symbol=self.active_bot.pair, amount=amount, isIsolated=True
                )
                repay_details_res: BinanceRepayRecords = (
                    self.client.get_margin_repay_details(
                        asset=asset, isolatedSymbol=self.active_bot.pair
                    )
                )
                repay_details = repay_details_res["rows"][0]
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

                self.client.transfer_isolated_margin_to_spot(
                    asset=self.active_bot.balance_to_use, symbol=self.active_bot.pair, amount=amount
                )

                self.active_bot.deal.buy_total_qty = amount_to_borrow
                completion_msg = f"Margin_short bot repaid, funds transferred back to SPOT. Bot completed"
                self.active_bot.errors.append(completion_msg)
                print(completion_msg)

                # In the future, amount_to_borrow = base + base * (2.5)
                amount_to_borrow = self.active_bot.base_order_size
                margin_loan_transaction = self.client.create_margin_loan(
                    asset=asset, amount=amount_to_borrow, isIsolated=True
                )
                
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

            except BinanceAPIException as error:
                raise MarginShortError(
                    f"Unable to terminate margin_short transfer transaction: {error}"
                )


    def margin_short_base_order(self):
        """
        Same functionality as usual base_order
        with a few more fields. This is used during open_deal

        1. Check margin account balance
        2. Carry on with usual base_order
        """
        print(f"Opening margin margin_long_base_order")
        
        initial_price = float(self.matching_engine(self.active_bot.pair, True))
        qty = round_numbers(
            (float(self.active_bot.base_order_size) / float(initial_price)),
            self.qty_precision,
        )
        if self.db_collection.name == "bots":
            self.init_margin_short()
            # Margin sell
            order_res = self.sell_order(qty)
        else:
            # Margin sell
            order_res = self.simulate_margin_order(
                qty, "SELL"
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
            marginBuyBorrowAmount=order_res["marginBuyBorrowAmount"],
            marginBuyBorrowAsset=order_res["marginBuyBorrowAsset"],
            isIsolated=order_res["isIsolated"],
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

        self.active_bot.deal.stop_loss_price = self.active_bot.deal.buy_price - (self.active_bot.deal.buy_price * (float(self.active_bot.stop_loss) / 100))

        # Direction 1: upward trend
        # Future feature: trailling
        if price < self.active_bot.deal.take_profit_price:
            self.terminate_margin_short()
        
        # Direction 2: downard trend
        elif price > 0 and price > self.active_bot.deal.stop_loss_price:
            self.execute_stop_loss(price)
        
        else:
            return

    def set_margin_short_stop_loss(self):
        """
        Sets stop_loss for margin_short at initial activation
        """
        price = self.active_bot.deal.buy_price
        if (
            hasattr(self.active_bot, "stop_loss")
            and float(self.active_bot.stop_loss) > 0
        ):
            stop_loss_price = price - (price * (float(self.active_bot.stop_loss) / 100))
            self.active_bot.deal.margin_short_stop_loss_price = stop_loss_price

            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")  # _id is what causes conflict not id

            document = self.db_collection.find_one_and_update(
                {"id": self.active_bot.id},
                {"$set": bot},
                return_document=ReturnDocument.AFTER,
            )

            return document

        bot = encode_json(self.active_bot)
        return bot


    def execute_stop_loss(self, close_price=0):
        """
        Execute stop loss when price is hit
        This is used during streaming updates
        """
        qty = None
        if self.db_collection.name == "bots":
            qty = self.compute_isolated_qty(self.active_bot.pair)

        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        if self.db_collection.name == "bots" and not qty:
            self.update_deal_logs(
                f"Cannot execute update stop limit, quantity is {qty}. Deleting bot"
            )
            params = {"id": self.active_bot.id}
            self.bb_request(f"{self.bb_bot_url}", "DELETE", params=params)
            return
    
        order_id = None
        for order in self.active_bot.orders:
            if order.deal_type == "margin_short_take_profit":
                order_id = order.order_id
                self.active_bot.orders.remove(order)
                break

        if order_id:
            try:
                # First cancel old order to unlock balance
                self.client.cancel_margin_order(
                symbol=self.active_bot.pair,
                orderId=order_id)
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs("Take profit order not found, no need to cancel")
                return

        if qty:
            price = float(self.matching_engine(self.active_bot.pair, True, qty))

        # Margin buy (buy back)
        if self.db_collection.name == "paper_trading":
            res = self.simulate_margin_order(self.active_bot.deal.buy_total_qty, "BUY")
        else:
            try:
                res = self.client.create_margin_order(
                    symbol=self.active_bot.pair,
                    side="BUY",
                    type="LIMIT",
                    timeInForce="GTC",
                    quantity=qty,
                    price=supress_notation(price, self.price_precision))
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
            error_msg = "Failed to execute stop loss order (status NEW), retrying..."
            self.update_deal_logs(error_msg)
            raise Exception(error_msg)
            # Not retry for now, as it can cause an infinite loop
            # self.execute_stop_loss(price)

        stop_loss_order = MarginOrderSchema(
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
            marginBuyBorrowAmount=res["marginBuyBorrowAmount"],
            marginBuyBorrowAsset=res["marginBuyBorrowAsset"],
            isIsolated=res["isIsolated"],
        )

        commission = 0
        for chunk in res["fills"]:
            commission += float(chunk["commission"])

        self.active_bot.orders.append(stop_loss_order)

        # Guard against type errors
        # These errors are sometimes hard to debug, it takes hours
        deal = DealSchema(
            sell_price = res["price"],
            sell_qty = res["origQty"],
            sell_timestamp = res["transactTime"]
        )
        self.active_bot.deal = deal

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

