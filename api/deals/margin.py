from time import time
from datetime import datetime
from urllib.error import HTTPError

from binance.exceptions import BinanceAPIException
from deals.schema import DealSchema
from tools.enum_definitions import Strategy
from bots.schemas import BotSchema
from tools.enum_definitions import Status
from deals.base import BaseDeal
from deals.schema import MarginOrderSchema
from pydantic import ValidationError
from tools.handle_error import QuantityTooLow, encode_json
from tools.round_numbers import round_numbers, supress_notation


class MarginShortError(Exception):
    pass


class MarginDeal(BaseDeal):
    def __init__(self, bot, db_collection: str) -> None:
        # Inherit from parent class
        super().__init__(bot, db_collection)

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

    def get_isolated_balance(self, symbol=None):
        """
        Get balance of Isolated Margin account

        Use isolated margin account is preferrable,
        because this is the one that supports the most assets
        """
        info = self.signed_request(url=self.isolated_account, payload={"symbols": symbol})
        assets = info["assets"]
        return assets

    def compute_margin_buy_back(
        self,
    ):
        """
        Same as compute_qty but with isolated margin balance

        Find available amount to buy_back
        this is the borrowed amount
        """
        balance = self.get_isolated_balance(symbol=self.active_bot.pair)
        if len(balance) == 0 or balance[0]["baseAsset"]["borrowed"] == 0:
            return None
        qty = float(balance[0]["baseAsset"]["borrowed"]) + float(balance[0]["baseAsset"]["interest"])
        return round_numbers(qty, self.qty_precision)

    def get_remaining_quote_asset(self):
        balance = self.get_isolated_balance(symbol=self.active_bot.pair)
        if len(balance) == 0 or balance[0]["baseAsset"]["borrowed"] == 0:
            return None
        qty = float(balance[0]["quoteAsset"]["free"])
        return round_numbers(qty, self.qty_precision)

    def init_margin_short(self, qty):
        """
        Pre-tasks for db_collection = bots
        These tasks are not necessary for paper_trading

        1. transfer funds
        2. create loan with qty given by market
        3. borrow 2.5x to do base order
        """
        print("Initializating margin_short tasks for real bots trading")
        # Check margin account balance first
        balance = self.get_isolated_balance(self.active_bot.pair)
        if len(balance) == 0:
            try:
                # transfer
                self.client.transfer_spot_to_isolated_margin(
                    asset=self.active_bot.balance_to_use,
                    symbol=self.active_bot.pair,
                    amount=self.active_bot.base_order_size,
                )
            except BinanceAPIException as error:
                if error.code == -11003:
                    raise MarginShortError("Isolated margin not available")
                # Enable
                self.client.enable_isolated_margin_account(
                    symbol=self.active_bot.pair
                )
            except Exception as error:
                print(error)
                

        asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
        # In the future, amount_to_borrow = base + base * (2.5)
        self.client.create_margin_loan(
            asset=asset, symbol=self.active_bot.pair, amount=qty, isIsolated=True
        )
        loan_details = self.client.get_margin_loan_details(asset=asset, isolatedSymbol=self.active_bot.pair)
        fee_details = self.signed_request(self.isolated_fee_url, payload={"symbol": self.active_bot.pair})
        self.active_bot.deal.margin_short_loan_timestamp = loan_details["rows"][0]["timestamp"]
        self.active_bot.deal.margin_short_loan_principal = loan_details["rows"][0]["principal"]
        self.active_bot.deal.margin_loan_id = loan_details["rows"][0]["txId"]
        self.active_bot.deal.margin_short_loan_interest = float(next((item["dailyInterest"] for item in fee_details[0]["data"] if item["coin"] == asset), 0))

        return

    def terminate_margin_short(self):
        """

        1. buy back
        2. repay loan
        2. transfer back to spot
        """
        print("Terminating margin_short tasks for real bots trading")

        # Check margin account balance first
        balance = self.get_isolated_balance(self.active_bot.pair)
        if len(balance) > 0:
            # repay
            asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
            repay_amount = round_numbers(float(balance[0]["baseAsset"]["borrowed"]) + float(balance[0]["baseAsset"]["interest"]), self.qty_precision)
            # Check if there is a loan
            # Binance may reject loans if they don't have asset
            # or binbot errors may transfer funds but no loan is created
            query_loan = self.signed_request(url=self.loan_record, payload={"asset": asset, "isolatedSymbol": self.active_bot.pair})
            if query_loan["total"] > 0 and repay_amount > 0:
                repay_amount = round_numbers(repay_amount, self.qty_precision)
                self.client.repay_margin_loan(
                    asset=asset,
                    symbol=self.active_bot.pair,
                    amount=repay_amount,
                    isIsolated="TRUE",
                )

                repay_details_res = (
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

                # Sell quote and get base asset (USDT)
                balance = self.get_isolated_balance(self.active_bot.pair)
                # In theory, we should sell self.active_bot.base_order
                # but this can be out of sync
                sell_back_qty = supress_notation(balance[0]["baseAsset"]["free"], self.qty_precision)
                res = self.sell_order(sell_back_qty)
                sell_back_order = MarginOrderSchema(
                    timestamp=res["transactTime"],
                    deal_type="take_profit",
                    order_id=res["orderId"],
                    pair=res["symbol"],
                    order_side=res["side"],
                    order_type=res["type"],
                    price=res["price"],
                    qty=res["origQty"],
                    fills=res["fills"],
                    time_in_force=res["timeInForce"],
                    status=res["status"],
                    is_isolated=res["isIsolated"],
                )

                for chunk in res["fills"]:
                    self.active_bot.total_commission += float(chunk["commission"])

                self.active_bot.orders.append(sell_back_order)

                self.active_bot.deal.margin_short_buy_back_price = res["price"]
                self.active_bot.deal.buy_total_qty = res["origQty"]
                self.active_bot.deal.margin_short_buy_back_timestamp = res["transactTime"]
                self.active_bot.status = Status.completed
            else:
                self.active_bot.status = Status.error
                self.active_bot.errors.append("Loan not found for this bot.")

            # Save in two steps, because it takes time for Binance to process repayments
            bot = self.save_bot_streaming()
            self.active_bot = BotSchema.parse_obj(bot)

            try:
                # transfer back to SPOT account
                self.client.transfer_isolated_margin_to_spot(
                    asset=self.active_bot.balance_to_use,
                    symbol=self.active_bot.pair,
                    amount=balance[0]["quoteAsset"]["free"],
                )
            except BinanceAPIException as error:
                print(error)

            if self.get_remaining_quote_asset() > 0:
                # transfer back any quote asset qty leftovers
                self.client.transfer_isolated_margin_to_spot(
                    asset=asset,
                    symbol=self.active_bot.pair,
                    amount=balance[0]["baseAsset"]["free"],
                )

            # Disable isolated pair to avoid reaching the 15 pair limit
            self.client.disable_isolated_margin_account(
                symbol=self.active_bot.pair
            )

            completion_msg = f"Margin_short bot repaid, funds transferred back to SPOT."
            self.active_bot.errors.append(completion_msg)
            print(completion_msg)

            bot = self.save_bot_streaming()

            return bot


    def margin_short_base_order(self):
        """
        Same functionality as usual base_order
        with a few more fields. This is used during open_deal

        1. Check margin account balance
        2. Carry on with usual base_order
        """
        print(f"Opening margin_short_base_order")
        initial_price = float(self.matching_engine(self.active_bot.pair, True))
        # Given USDT amount we want to buy,
        # how much can we buy?
        qty = round_numbers(
            (float(self.active_bot.base_order_size) / float(initial_price)),
            self.qty_precision,
        )
        if qty == 0:
            raise QuantityTooLow("Margin short quantity is too low")

        if self.db_collection.name == "bots":
            self.init_margin_short(qty)

            # Margin sell
            order_res = self.sell_order(qty)
        else:
            # Simulate Margin sell
            order_res = self.simulate_margin_order(qty, "SELL")

        order_data = MarginOrderSchema(
            timestamp=order_res["transactTime"],
            order_id=order_res["orderId"],
            deal_type="base_order",
            pair=order_res["symbol"],
            order_side=order_res["side"],
            order_type=order_res["type"],
            price=order_res["price"],
            qty=order_res["origQty"],
            fills=order_res["fills"],
            time_in_force=order_res["timeInForce"],
            status=order_res["status"],
            is_isolated=order_res["isIsolated"],
        )

        self.active_bot.orders.append(order_data)

        self.active_bot.deal.margin_short_sell_timestamp = order_res["transactTime"]
        self.active_bot.deal.margin_short_sell_price = float(order_res["price"])
        self.active_bot.deal.buy_total_qty = float(order_res["origQty"])
        self.active_bot.deal.margin_short_base_order = float(order_res["origQty"])

        # Estimate interest to add to total cost
        isolated_fees = self.signed_request(url=self.isolated_fee_url, payload={"symbol": self.active_bot.pair})
        # for the following computation check https://www.binance.com/en/margin-fee
        self.active_bot.deal.hourly_interest_rate = float(isolated_fees[0]["data"][0]["dailyInterest"]) / 24

        # Activate bot
        self.active_bot.status = Status.active
        return self.active_bot

    def streaming_updates(self, close_price: str, open_price: str):
        """
        Margin_short streaming updates
        """

        price = float(close_price)
        self.active_bot.deal.current_price = price
        self.active_bot.deal.stop_loss_price = (
            self.active_bot.deal.margin_short_sell_price
            + (
                self.active_bot.deal.margin_short_sell_price
                * (float(self.active_bot.stop_loss) / 100)
            )
        )
        print(f"margin_short streaming updating {self.active_bot.pair} @ {self.active_bot.deal.stop_loss_price}")

        # Direction 1.1: downward trend (short)
        # Breaking trailling
        if (
            price > 0
            and self.active_bot.deal.take_profit_price > 0
            and price < self.active_bot.deal.take_profit_price
        ):
            
            if self.active_bot.trailling == "true" and self.active_bot.deal.margin_short_sell_price > 0:

                self.update_trailling_profit(close_price)
                bot = self.save_bot_streaming()
                self.active_bot = BotSchema.parse_obj(bot)


                # Direction 2 (downward): breaking the trailling_stop_loss
                # Make sure it's red candlestick, to avoid slippage loss
                # Sell after hitting trailling stop_loss and if price already broken trailling
                if (
                    float(self.active_bot.deal.trailling_stop_loss_price) > 0
                    # Broken stop_loss
                    and float(close_price)
                    < float(self.active_bot.deal.trailling_stop_loss_price)
                    # Red candlestick
                    and (float(open_price) > float(close_price))
                ):
                    print(
                        f'Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Selling {self.active_bot.pair}'
                    )
                    # since price is given by matching engine
                    # execute_take_profit = trailling_profit
                    self.execute_take_profit()
                    if self.db_collection.name == "bots":
                        self.terminate_margin_short()

                    self.update_required()


            else:

                print(f'Executing margin_short take_profit after hitting take_profit_price {self.active_bot.deal.stop_loss_price}')
                self.execute_take_profit()
                if self.db_collection.name == "bots":
                    self.terminate_margin_short()
                self.update_required()

        # Direction 1.2: upward trend (short)
        # Not breaking trailling
        if (
            price > 0
            and self.active_bot.deal.stop_loss_price > 0
            and price > self.active_bot.deal.stop_loss_price
        ):
            print(f'Executing margin_short stop_loss reversal after hitting stop_loss_price {self.active_bot.deal.stop_loss_price}')
            self.execute_stop_loss()
            if self.db_collection.name == "bots":
                self.terminate_margin_short()

            # To profit from reversal, we still need to repay loan and transfer
            # assets back to SPOT account, so this means executing stop loss
            # and creating a new long bot, this way we can also keep the old bot
            # with the corresponding data for profit/loss calculation
            self.create_long_bot()
            self.update_required()

        try:
            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            self.db_collection.update_one(
                {"id": self.active_bot.id},
                {"$set": bot},
            )

        except ValidationError as error:
            self.update_deal_logs(f'margin_short steaming update error: {error}')
            return
        except (TypeError, AttributeError) as error:
            message = str(";".join(error.args))
            self.update_deal_logs(f'margin_short steaming update error: {message}')
            return
        except Exception as error:
            self.update_deal_logs(f'margin_short steaming update error: {error}')
            return

        return

    def set_margin_short_stop_loss(self):
        """
        Sets stop_loss for margin_short at initial activation
        """
        price = float(self.active_bot.deal.margin_short_sell_price)
        if (
            hasattr(self.active_bot, "stop_loss")
            and float(self.active_bot.stop_loss) > 0
        ):
            self.active_bot.deal.stop_loss_price = price + (price * (float(self.active_bot.stop_loss) / 100))

        return self.active_bot

    def set_margin_take_profit(self):
        """
        Sets take_profit for margin_short at initial activation
        """
        price = float(self.active_bot.deal.margin_short_sell_price)
        if (
            hasattr(self.active_bot, "take_profit")
            and float(self.active_bot.take_profit) > 0
        ):
            take_profit_price = price - (
                price * (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price

        return self.active_bot

    def execute_stop_loss(self):
        """
        Execute stop loss when price is hit
        This is used during streaming updates
        """
        qty = 1
        if self.db_collection.name == "bots":
            qty = self.compute_margin_buy_back()

        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        # if self.db_collection.name == "bots" and not qty:
        #     self.update_deal_logs(
        #         f"Cannot execute update stop limit, quantity is {qty}. Deleting bot"
        #     )
        #     params = {"id": self.active_bot.id}
        #     self.bb_request(f"{self.bb_bot_url}", "DELETE", params=params)
        #     return

        order_id = None
        for order in self.active_bot.orders:
            if order.deal_type == "stop_loss":
                order_id = order.order_id
                self.active_bot.orders.remove(order)
                break

        if order_id:
            try:
                # First cancel old order to unlock balance
                self.client.cancel_margin_order(
                    symbol=self.active_bot.pair, orderId=order_id
                )
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs("Take profit order not found, no need to cancel")
                return

        price = self.matching_engine(self.active_bot.pair, True, qty)
        # Margin buy (buy back)
        if self.db_collection.name == "paper_trading":
            res = self.simulate_margin_order(self.active_bot.deal.buy_total_qty, "BUY")
        else:
            try:
                res = self.buy_order(price, qty)
            except QuantityTooLow as error:
                # Delete incorrectly activated or old bots
                self.bb_request(f"{self.bb_bot_url}/{self.active_bot.id}", "DELETE")
                print(f"Deleted obsolete bot {self.active_bot.pair}")
            except BinanceAPIException as error:
                # Not enough funds probably because already bought before
                # correct using quote asset to buy base asset
                # we want base asset anyway now, because of long bot
                if error.code == -2010:
                    quote_asset_qty = self.get_remaining_quote_asset()
                    price = self.matching_engine(self.active_bot.pair, False, qty)
                    qty = round_numbers(float(quote_asset_qty) / float(price), self.qty_precision)
                    res = self.buy_order(price, qty)
            except Exception as error:
                self.update_deal_logs(
                    f"Error trying to open new stop_limit order {error}"
                )
                return
            

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
            is_isolated=res["isIsolated"],
        )

        for chunk in res["fills"]:
            self.active_bot.total_commission += float(chunk["commission"])

        self.active_bot.orders.append(stop_loss_order)

        # Guard against type errors
        # These errors are sometimes hard to debug, it takes hours
        self.active_bot.deal.margin_short_buy_back_price = res["price"]
        self.active_bot.deal.buy_total_qty = res["origQty"]
        self.active_bot.deal.margin_short_buy_back_timestamp = res["transactTime"]

        msg = f"Completed Stop loss order"
        self.active_bot.errors.append(msg)

        return

    def execute_take_profit(self):
        """
        Execute take profit when price is hit
        Buy back asset sold
        """
        qty = 1
        if self.db_collection.name == "bots":
            qty = self.compute_margin_buy_back()

        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        # if self.db_collection.name == "bots" and not qty:
        #     self.update_deal_logs(
        #         f"Cannot execute update stop limit, quantity is {qty}. Deleting bot"
        #     )
        #     params = {"id": self.active_bot.id}
        #     self.bb_request(f"{self.bb_bot_url}", "DELETE", params=params)
        #     return

        order_id = None
        for order in self.active_bot.orders:
            if order.deal_type == "take_profit":
                order_id = order.order_id
                self.active_bot.orders.remove(order)
                break

        if order_id:
            try:
                # First cancel old order to unlock balance
                self.client.cancel_margin_order(
                    symbol=self.active_bot.pair, orderId=order_id
                )
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs("Take profit order not found, no need to cancel")
                return

        if qty:
            price = self.matching_engine(self.active_bot.pair, True, qty)

        # Margin buy (buy back)
        if self.db_collection.name == "paper_trading":
            res = self.simulate_margin_order(self.active_bot.deal.buy_total_qty, "BUY")
        else:
            try:
                res = self.buy_order(price=supress_notation(price, self.price_precision), qty=supress_notation(qty, self.qty_precision))
            except QuantityTooLow as error:
                # Delete incorrectly activated or old bots
                self.bb_request(f"{self.bb_bot_url}/{self.active_bot.id}", "DELETE")
                print(f"Deleted obsolete bot {self.active_bot.pair}")
            except Exception as error:
                self.update_deal_logs(
                    f"Error trying to open new stop_limit order {error}"
                )
                return

        take_profit_order = MarginOrderSchema(
            timestamp=res["transactTime"],
            deal_type="take_profit",
            order_id=res["orderId"],
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res["price"],
            qty=res["origQty"],
            fills=res["fills"],
            time_in_force=res["timeInForce"],
            status=res["status"],
            is_isolated=res["isIsolated"],
        )

        for chunk in res["fills"]:
            self.active_bot.total_commission += float(chunk["commission"])

        self.active_bot.orders.append(take_profit_order)
        msg = f"Completed Take profit!"
        self.active_bot.errors.append(msg)
        self.active_bot.status = Status.completed

        return

    def create_long_bot(self):
        """
        Switch to long strategy:

        1. Change strategy type
        2. Open long strategy deal as usual (open_deal)
        3. Set margin_short variables to 0
        4. Repay loan
        """

        # Reset bot to prepare for new activation
        del self.active_bot.deal
        del self.active_bot.orders
        self.active_bot.strategy = Strategy.long
        self.save_bot_streaming()

        # Create and activate bot using a network request
        # otherwise we get circular import (Create) or duplicated code
        bot = self.active_bot.dict()

        created_bot = self.signed_request(url=self.bb_bot_url, method="POST", payload=bot)
        if created_bot["error"] == 0:
            reactivated_bot = self.request(url=f"{self.bb_activate_bot_url}/{self.active_bot.id}")
            print("Created a reversal bot (margin_short -> long)", reactivated_bot)

        return

    def update_trailling_profit(self, close_price):

        if self.active_bot.deal.trailling_stop_loss_price == 0:
            trailling_price = float(self.active_bot.deal.margin_short_sell_price) - (
                self.active_bot.deal.margin_short_sell_price * ((self.active_bot.take_profit) / 100)
            )
            # If trailling_stop_loss < base order it will reset every time
            print(
                f"{datetime.utcnow()} {self.active_bot.pair} Setting trailling_stop_loss (short)"
            )
        else:

            # Current take profit + next take_profit
            trailling_price = float(self.active_bot.deal.take_profit_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            print(
                f"{datetime.utcnow()} {self.active_bot.pair} Updated (Didn't break trailling), updating trailling price points (short)"
            )
        
        # Direction 1 (upward): breaking the current trailling
        if float(close_price) <= float(trailling_price):
            new_take_profit = float(trailling_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            new_trailling_stop_loss = float(trailling_price) * (
                1 + (float(self.active_bot.trailling_deviation) / 100)
            )
            # Update deal take_profit
            self.active_bot.deal.take_profit_price = new_take_profit
            # take_profit but for trailling, to avoid confusion
            # trailling_profit_price always be > trailling_stop_loss_price
            self.active_bot.deal.trailling_profit_price = new_take_profit

            if new_trailling_stop_loss > self.active_bot.deal.margin_short_sell_price:
                # Selling below buy_price will cause a loss
                # instead let it drop until it hits safety order or stop loss
                print(
                    f"{self.active_bot.pair} Updating take_profit_price, trailling_profit and trailling_stop_loss_price! {new_take_profit}"
                )
                # Update trailling_stop_loss
                self.active_bot.deal.trailling_stop_loss_price = new_trailling_stop_loss
                print(
                    f'{datetime.utcnow()} Updated {self.active_bot.pair} trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}'
                )
            else:
                # Protect against drops by selling at buy price + 0.75% commission
                self.active_bot.deal.trailling_stop_loss_price = (
                    float(self.active_bot.deal.buy_price) * 1.075
                )
                print(
                    f'{datetime.utcnow()} Updated {self.active_bot.pair} trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}'
                )
            
        self.save_bot_streaming()
