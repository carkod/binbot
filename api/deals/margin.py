import logging

from time import time
from datetime import datetime
from urllib.error import HTTPError

from binance.exceptions import BinanceAPIException
from tools.handle_error import BinanceErrors
from deals.schema import DealSchema
from tools.enum_definitions import Strategy
from bots.schemas import BotSchema
from tools.enum_definitions import Status
from deals.base import BaseDeal
from deals.schema import MarginOrderSchema
from pydantic import ValidationError
from tools.handle_error import QuantityTooLow, encode_json, BinanceErrors
from tools.round_numbers import (
    round_numbers,
    supress_notation,
    supress_trailling,
    round_numbers_ceiling,
)


class MarginShortError(Exception):
    pass


class MarginDeal(BaseDeal):
    def __init__(self, bot, db_collection: str) -> None:
        # Inherit from parent class
        super().__init__(bot, db_collection)
        self.isolated_balance = self.get_isolated_balance(self.active_bot.pair)

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

    def compute_margin_buy_back(
        self,
    ):
        """
        Same as compute_qty but with isolated margin balance

        Find available amount to buy_back
        this is the borrowed amount + interests.
        Decimals have to be rounded up to avoid leaving
        "leftover" interests
        """

        if (
            self.isolated_balance[0]["quoteAsset"]["free"] == 0
            or self.isolated_balance[0]["baseAsset"]["borrowed"] == 0
        ):
            return None

        qty = float(self.isolated_balance[0]["baseAsset"]["borrowed"]) + float(
            self.isolated_balance[0]["baseAsset"]["interest"]
        )

        return round_numbers_ceiling(qty, self.qty_precision), float(
            self.isolated_balance[0]["baseAsset"]["free"]
        )

    def get_remaining_quote_asset(self):
        if (
            self.isolated_balance[0]["quoteAsset"]["free"] == 0
            or self.isolated_balance[0]["baseAsset"]["borrowed"] == 0
        ):
            return None

        qty = float(self.isolated_balance[0]["quoteAsset"]["free"])
        return round_numbers(qty, self.qty_precision)

    def cancel_open_orders(self, deal_type):
        """
        Given an order deal_type i.e. take_profit, stop_loss etc
        cancel currently open orders to unblock funds
        """

        order_id = None
        for order in self.active_bot.orders:
            if order.deal_type == deal_type:
                order_id = order.order_id
                self.active_bot.orders.remove(order)
                break

        if order_id:
            try:
                # First cancel old order to unlock balance
                self.cancel_margin_order(symbol=self.active_bot.pair, orderId=order_id)
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs("Take profit order not found, no need to cancel")
                return

        return

    def init_margin_short(self, qty):
        """
        Pre-tasks for db_collection = bots
        These tasks are not necessary for paper_trading

        1. transfer funds
        2. create loan with qty given by market
        3. borrow 2.5x to do base order
        """
        logging.info("Initializating margin_short tasks for real bots trading")
        # Check margin account balance first
        balance = float(self.isolated_balance[0]["quoteAsset"]["free"])
        # always enable, it doesn't cause errors
        self.enable_isolated_margin_account(symbol=self.active_bot.pair)
        if balance == 0:
            try:
                # transfer
                self.transfer_spot_to_isolated_margin(
                    asset=self.active_bot.balance_to_use,
                    symbol=self.active_bot.pair,
                    amount=self.active_bot.base_order_size,
                )
            except BinanceAPIException as error:
                if error.code == -11003:
                    raise MarginShortError("Isolated margin not available")

        asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
        # In the future, amount_to_borrow = base + base * (2.5)
        try:
            self.create_margin_loan(
                asset=asset, symbol=self.active_bot.pair, amount=qty
            )
            loan_details = self.get_margin_loan_details(asset=asset, isolatedSymbol=self.active_bot.pair)

            self.active_bot.deal.margin_short_loan_timestamp = loan_details["rows"][0]["timestamp"]
            self.active_bot.deal.margin_short_loan_principal = loan_details["rows"][0]["principal"]
            self.active_bot.deal.margin_loan_id = loan_details["rows"][0]["txId"]

            # Estimate interest to add to total cost
            asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
            # This interest rate is much more accurate than any of the others
            hourly_fees = self.signed_request(url=self.isolated_hourly_interest, payload={"assets": asset, "isIsolated": "TRUE"})
            self.active_bot.deal.hourly_interest_rate = float(hourly_fees[0]["nextHourlyInterestRate"])

        except BinanceErrors as error:
            logging.error(error)
            return
        except Exception as error:
            logging.error(error)

        return

    def terminate_margin_short(self, buy_back_fiat: bool = True):
        """

        Args:
        - buy_back_fiat. By default it will buy back USDT (sell asset and transform into USDT)

        In the case of reversal, we don't want to do this additional transaction, as it will incur
        in an additional cost. So this is added to skip that section

        1. Repay loan
        2. Exchange asset to quote asset (USDT)
        3. Transfer back to spot
        """
        logging.info("Terminating margin_short tasks for real bots trading")

        # Check margin account balance first
        balance = float(self.isolated_balance[0]["quoteAsset"]["free"])
        if balance > 0:
            # repay
            asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
            repay_amount = float(
                self.isolated_balance[0]["baseAsset"]["borrowed"]
            ) + float(self.isolated_balance[0]["baseAsset"]["interest"])
            # Check if there is a loan
            # Binance may reject loans if they don't have asset
            # or binbot errors may transfer funds but no loan is created
            query_loan = self.signed_request(
                url=self.loan_record_url,
                payload={"asset": asset, "isolatedSymbol": self.active_bot.pair},
            )
            if query_loan["total"] > 0 and repay_amount > 0:
                # Only supress trailling 0s, so that everything is paid
                # repay_amount = supress_trailling(repay_amount)
                try:
                    self.repay_margin_loan(
                        asset=asset,
                        symbol=self.active_bot.pair,
                        amount=repay_amount,
                        isIsolated="TRUE",
                    )
                    # Complete bot here to avoid unimportant errors blocking completion
                    # Once margin loan is repaid it is closed profit
                    self.active_bot.status = Status.completed
                except BinanceAPIException as error:
                    if error.code == -3041:
                        # Most likely not enough funds to pay back
                        # Get fiat (USDT) to pay back
                        self.active_bot.errors.append(error.message)
                        pass

                repay_details_res = self.get_margin_repay_details(
                    asset=asset, isolatedSymbol=self.active_bot.pair
                )
                if len(repay_details_res["rows"]) > 0:
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

                if buy_back_fiat:
                    # Sell quote and get base asset (USDT)
                    # In theory, we should sell self.active_bot.base_order
                    # but this can be out of sync
                    sell_back_qty = supress_notation(
                        self.isolated_balance[0]["baseAsset"]["free"],
                        self.qty_precision,
                    )
                    res = self.sell_margin_order(
                        symbol=self.active_bot.pair, qty=sell_back_qty
                    )
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
                    self.active_bot.deal.margin_short_buy_back_timestamp = res[
                        "transactTime"
                    ]
                    self.active_bot.status = Status.completed
                    self.active_bot.errors.append(
                        "Margin_short bot repaid, deal completed."
                    )

            else:
                self.active_bot.status = Status.error
                self.active_bot.errors.append("Loan not found for this bot.")

            # Save in two steps, because it takes time for Binance to process repayments
            bot = self.save_bot_streaming()
            self.active_bot: BotSchema = BotSchema.parse_obj(bot)

            if float(self.isolated_balance[0]["quoteAsset"]["free"]) != 0:
                try:
                    # transfer back to SPOT account
                    self.transfer_isolated_margin_to_spot(
                        asset=self.active_bot.balance_to_use,
                        symbol=self.active_bot.pair,
                        amount=self.isolated_balance[0]["quoteAsset"]["free"],
                    )
                except BinanceAPIException as error:
                    logging.error(error)

            # if (
            #     self.get_remaining_quote_asset() > 0
            #     and float(self.isolated_balance[0]["baseAsset"]["free"]) > 0
            # ):
                # transfer back any quote asset qty leftovers
            print("Transfering base asset back to Spot")
            self.transfer_isolated_margin_to_spot(
                asset=asset,
                symbol=self.active_bot.pair,
                amount=self.isolated_balance[0]["baseAsset"]["free"],
            )

            # Disable isolated pair to avoid reaching the 15 pair limit
            # this is not always possible, sometimes there are small quantities
            # that can't be cleaned out completely, need to do it manually
            # this is ok, since this is not a hard requirement to complete the deal
            try:
                self.disable_isolated_margin_account(
                    symbol=self.active_bot.pair
                )
            except BinanceAPIException as error:
                logging.error(error)
                if error.code == -3051:
                    self.active_bot.errors.append(error.message)
                    pass

            completion_msg = f"{self.active_bot.pair} ISOLATED margin funds transferred back to SPOT."
            self.active_bot.errors.append(completion_msg)
            logging.info(completion_msg)
            bot = self.save_bot_streaming()

            return bot

    def margin_short_base_order(self):
        """
        Same functionality as usual base_order
        with a few more fields. This is used during open_deal

        1. Check margin account balance
        2. Carry on with usual base_order
        """
        logging.info(f"Opening margin_short_base_order")
        initial_price = float(self.matching_engine(self.active_bot.pair, False))
        # Given USDT amount we want to buy,
        # how much can we buy?
        qty = round_numbers_ceiling(
            (float(self.active_bot.base_order_size) / float(initial_price)),
            self.qty_precision,
        )
        # Prepare for margin sell
        # Add markup on top of qty to cover for stop_losses
        # and round up so that we don't have leftovers
        qty = round_numbers_ceiling(
            qty * (1 * self.active_bot.stop_loss), self.qty_precision
        )
        if qty == 0:
            raise QuantityTooLow("Margin short quantity is too low")

        if self.db_collection.name == "bots":
            self.init_margin_short(qty)
            order_res = self.sell_margin_order(symbol=self.active_bot.pair, qty=qty)
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

        # Activate bot
        self.active_bot.status = Status.active
        return self.active_bot

    def streaming_updates(self, close_price: str):
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
        self.active_bot.deal.margin_short_loan_interest = float(
            self.active_bot.deal.margin_short_loan_principal
        ) * float(self.active_bot.deal.hourly_interest_rate)
        # Add it to as part of total_commission for easy profit calculation
        self.active_bot.total_commission += float(
            self.active_bot.deal.margin_short_loan_principal
        ) * float(self.active_bot.deal.hourly_interest_rate)
        logging.debug(
            f"margin_short streaming updating {self.active_bot.pair} @ {self.active_bot.deal.stop_loss_price} and interests {self.active_bot.deal.margin_short_loan_interest}"
        )

        # Direction 1.1: downward trend (short)
        # Breaking trailling
        if (
            price > 0
            and self.active_bot.deal.take_profit_price > 0
            and price < self.active_bot.deal.take_profit_price
        ):
            if (
                self.active_bot.trailling == "true" or self.active_bot.trailling
            ) and self.active_bot.deal.margin_short_sell_price > 0:
                self.update_trailling_profit(price)
                bot = self.save_bot_streaming()
                self.active_bot = BotSchema.parse_obj(bot)

            else:
                # Execute the usual non-trailling take_profit
                logging.debug(
                    f"Executing margin_short take_profit after hitting take_profit_price {self.active_bot.deal.stop_loss_price}"
                )
                self.execute_take_profit()
                if self.db_collection.name == "bots":
                    self.terminate_margin_short()
                self.update_required()

        # Direction 2: upward trend (short). breaking the trailling_stop_loss
        # Make sure it's red candlestick, to avoid slippage loss
        # Sell after hitting trailling stop_loss and if price already broken trailling
        if (
            float(self.active_bot.deal.trailling_stop_loss_price) > 0
            # Broken stop_loss
            and float(close_price)
            >= float(self.active_bot.deal.trailling_stop_loss_price)
            # Red candlestick
            # and (float(open_price) > float(close_price))
        ):
            logging.info(
                f"Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Selling {self.active_bot.pair}"
            )
            # since price is given by matching engine
            self.execute_take_profit(float(close_price))
            if self.db_collection.name == "bots":
                self.terminate_margin_short()

            self.update_required()

        # Direction 2: upward trend (short)
        # Not breaking trailling
        if (
            price > 0
            and self.active_bot.deal.stop_loss_price > 0
            and price > self.active_bot.deal.stop_loss_price
        ):
            logging.info(
                f"Executing margin_short stop_loss reversal after hitting stop_loss_price {self.active_bot.deal.stop_loss_price}"
            )
            self.execute_stop_loss()
            if self.db_collection.name == "bots":
                if (
                    hasattr(self.active_bot, "margin_short_reversal")
                    and self.active_bot.margin_short_reversal
                ):
                    # If we want to do reversal long bot, there is no point
                    # incurring in an additional transaction
                    self.terminate_margin_short(buy_back_fiat=False)
                else:
                    self.terminate_margin_short()

            # To profit from reversal, we still need to repay loan and transfer
            # assets back to SPOT account, so this means executing stop loss
            # and creating a new long bot, this way we can also keep the old bot
            # with the corresponding data for profit/loss calculation
            self.switch_to_long_bot()

        # Direction 1.3: upward trend (short)
        # Breaking trailling_stop_loss, completing trailling
        if (
            price > 0
            and self.active_bot.deal.stop_loss_price > 0
            and price > self.active_bot.deal.stop_loss_price
        ):
            logging.info(
                f"Executing margin_short stop_loss reversal after hitting stop_loss_price {self.active_bot.deal.stop_loss_price}"
            )
            self.execute_stop_loss()
            if self.db_collection.name == "bots":
                if (
                    hasattr(self.active_bot, "margin_short_reversal")
                    and self.active_bot.margin_short_reversal
                ):
                    # If we want to do reversal long bot, there is no point
                    # incurring in an additional transaction
                    self.terminate_margin_short(buy_back_fiat=False)
                else:
                    self.terminate_margin_short()

            # To profit from reversal, we still need to repay loan and transfer
            # assets back to SPOT account, so this means executing stop loss
            # and creating a new long bot, this way we can also keep the old bot
            # with the corresponding data for profit/loss calculation
            self.switch_to_long_bot()

        try:
            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            self.db_collection.update_one(
                {"id": self.active_bot.id},
                {"$set": bot},
            )
            self.update_required()

        except ValidationError as error:
            self.update_deal_logs(f"margin_short steaming update error: {error}")
            return
        except (TypeError, AttributeError) as error:
            message = str(";".join(error.args))
            self.update_deal_logs(f"margin_short steaming update error: {message}")
            return
        except Exception as error:
            self.update_deal_logs(f"margin_short steaming update error: {error}")
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
            self.active_bot.deal.stop_loss_price = price + (
                price * (float(self.active_bot.stop_loss) / 100)
            )

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
            qty, free = self.compute_margin_buy_back()

            # Cancel orders first
            # paper_trading doesn't have real orders so no need to check
            self.cancel_open_orders("stop_loss")

        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        # if self.db_collection.name == "bots" and not qty:
        #     self.update_deal_logs(
        #         f"Cannot execute update stop limit, quantity is {qty}. Deleting bot"
        #     )
        #     params = {"id": self.active_bot.id}
        #     self.bb_request(f"{self.bb_bot_url}", "DELETE", params=params)
        #     return

        # Margin buy (buy back)
        if self.db_collection.name == "paper_trading":
            res = self.simulate_margin_order(self.active_bot.deal.buy_total_qty, "BUY")
        else:
            try:
                if qty == 0 or free <= qty:
                    # Not enough funds probably because already bought before
                    # correct using quote asset to buy base asset
                    # we want base asset anyway now, because of long bot
                    quote_asset_qty = self.get_remaining_quote_asset()
                    price = self.matching_engine(self.active_bot.pair, True, qty)
                    qty = round_numbers(
                        float(quote_asset_qty) / float(price), self.qty_precision
                    )

                # If still qty = 0, it means everything is clear
                if qty == 0:
                    return

                res = self.buy_margin_order(
                    symbol=self.active_bot.pair, qty=qty, price=price
                )
            except BinanceAPIException as error:
                logging.error(error)
                if error.code in (-2010, -1013):
                    return
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

    def execute_take_profit(self, price=None):
        """
        Execute take profit when price is hit.
        This can be a simple take_profit order when take_profit_price is hit or
        a trailling_stop_loss when trailling_stop_loss_price is hit.
        This is because the only difference is the price and the price either provided
        by whatever triggers this sell or if not provided the matching_engine will provide it.

        This also sits well with the concept of "taking profit", which is closing a position at profit.

        - Buy back asset sold
        """
        qty = 1
        if self.db_collection.name == "bots":
            qty, free = self.compute_margin_buy_back()
            self.cancel_open_orders("take_profit")

        if qty and not price:
            price = self.matching_engine(self.active_bot.pair, True, qty)

        # Margin buy (buy back)
        if self.db_collection.name == "paper_trading":
            res = self.simulate_margin_order(self.active_bot.deal.buy_total_qty, "BUY")
        elif price:
            try:
                # Use market order
                res = self.buy_margin_order(
                    symbol=self.active_bot.pair,
                    price=price,
                    qty=supress_notation(qty, self.qty_precision),
                )
            except BinanceAPIException as error:
                if error.code == -2010:
                    self.update_deal_logs(
                        f"{error.message}. Not enough fiat to buy back loaned quantity"
                    )
                    return
            except BinanceErrors as error:
                message, code = error.args
                logging.error(message)
                if code == -2010:
                    return
                if code == -1102:
                    return

        else:
            try:
                if qty == 0 or free <= qty:
                    # Not enough funds probably because already bought before
                    # correct using quote asset to buy base asset
                    # we want base asset anyway now, because of long bot
                    quote_asset_qty = self.get_remaining_quote_asset()
                    price = self.matching_engine(self.active_bot.pair, True, qty)
                    qty = round_numbers(
                        float(quote_asset_qty) / float(price), self.qty_precision
                    )

                # If still qty = 0, it means everything is clear
                if qty == 0:
                    return

                res = self.buy_margin_order(
                    symbol=self.active_bot.pair,
                    price=supress_notation(price, self.price_precision),
                    qty=supress_notation(qty, self.qty_precision),
                )
            except QuantityTooLow as error:
                # Delete incorrectly activated or old bots
                self.bb_request(f"{self.bb_bot_url}/{self.active_bot.id}", "DELETE")
                logging.info(f"Deleted obsolete bot {self.active_bot.pair}")
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
        self.active_bot.deal.margin_short_buy_back_price = res["price"]
        self.active_bot.deal.margin_short_buy_back_timestamp = res["transactTime"]
        self.active_bot.deal.margin_short_buy_back_timestamp = res["transactTime"]
        msg = f"Completed Take profit!"
        self.active_bot.errors.append(msg)

        return

    def switch_to_long_bot(self):
        """
        Switch to long strategy.
        Doing some parts of open_deal from scratch
        this will allow us to skip one base_order and lower
        the initial buy_price

        Use open_deal as reference to create this new long bot deal:
        1. Find base_order in the orders list as in open_deal
        2. Calculate take_profit_price and stop_loss_price as usual
        3. Create deal
        """

        # Reset bot to prepare for new activation
        base_order = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == "base_order"
            ),
            None,
        )
        tp_price = float(base_order.price) * 1 + (
            float(self.active_bot.take_profit) / 100
        )
        if float(self.active_bot.stop_loss) > 0:
            stop_loss_price = base_order.price - (
                base_order.price * (float(self.active_bot.stop_loss) / 100)
            )
        else:
            stop_loss_price = 0

        self.active_bot.deal = DealSchema(
            buy_timestamp=base_order.timestamp,
            buy_price=base_order.price,
            buy_total_qty=base_order.qty,
            current_price=base_order.price,
            take_profit_price=tp_price,
            stop_loss_price=stop_loss_price,
        )
        self.active_bot.strategy = Strategy.long
        self.active_bot.status = Status.active
        self.active_bot.margin_short_reversal = False

        # Create and activate bot using a network request
        # otherwise we get circular import (Create) or duplicated code
        bot = self.active_bot.dict()
        return bot

    def update_trailling_profit(self, close_price):
        # Direction: downward trend (short)
        # Breaking trailling_stop_loss
        if self.active_bot.deal.trailling_stop_loss_price == 0:
            trailling_take_profit = float(
                self.active_bot.deal.margin_short_sell_price
            ) - (
                self.active_bot.deal.margin_short_sell_price
                * ((self.active_bot.take_profit) / 100)
            )
            stop_loss_trailling_price = float(trailling_take_profit) - (
                trailling_take_profit * ((self.active_bot.trailling_deviation) / 100)
            )
            # If trailling_stop_loss not below initial margin_short_sell price
            if stop_loss_trailling_price < self.active_bot.deal.margin_short_sell_price:
                self.active_bot.deal.trailling_stop_loss_price = (
                    stop_loss_trailling_price
                )
                bot = self.save_bot_streaming()
                self.active_bot = BotSchema.parse_obj(bot)
                logging.info(
                    f"{self.active_bot.pair} Setting trailling_stop_loss (short) and saved to DB"
                )

        if self.active_bot.deal.trailling_profit_price == 0:
            # Current take profit + next take_profit
            trailling_price = float(self.active_bot.deal.take_profit_price) - (
                float(self.active_bot.deal.take_profit_price)
                * (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.trailling_profit_price = trailling_price
            logging.info(
                f"{self.active_bot.pair} Updated (Didn't break trailling), updating trailling price points (short)"
            )

        # Keep trailling_stop_loss up to date
        if (
            self.active_bot.deal.trailling_stop_loss_price > 0
            and self.active_bot.deal.trailling_profit_price > 0
            and self.active_bot.deal.trailling_stop_loss_price
            < self.active_bot.deal.margin_short_sell_price
        ):
            self.active_bot.deal.trailling_stop_loss_price = float(
                self.active_bot.deal.trailling_profit_price
            ) * (1 + ((self.active_bot.trailling_deviation) / 100))
            logging.info(
                f"{self.active_bot.pair} Updating after broken first trailling_profit (short)"
            )

        # Direction 1 (downward): breaking the current trailling
        if float(close_price) <= float(self.active_bot.deal.trailling_profit_price):
            new_take_profit = float(self.active_bot.deal.trailling_profit_price) - (
                float(self.active_bot.deal.trailling_profit_price)
                * (float(self.active_bot.take_profit) / 100)
            )
            new_trailling_stop_loss = float(
                self.active_bot.deal.trailling_profit_price
            ) * (1 + (float(self.active_bot.trailling_deviation) / 100))
            # Update deal take_profit
            self.active_bot.deal.take_profit_price = new_take_profit
            # take_profit but for trailling, to avoid confusion
            # trailling_profit_price always be > trailling_stop_loss_price
            self.active_bot.deal.trailling_profit_price = new_take_profit

            # Update trailling_stop_loss
            if new_trailling_stop_loss < self.active_bot.deal.margin_short_sell_price:
                # Selling below buy_price will cause a loss
                # instead let it drop until it hits safety order or stop loss
                logging.info(
                    f"{self.active_bot.pair} Updating take_profit_price, trailling_profit and trailling_stop_loss_price! {new_take_profit}"
                )
                # Update trailling_stop_loss
                self.active_bot.deal.trailling_stop_loss_price = new_trailling_stop_loss
                logging.info(
                    f"{datetime.utcnow()} Updated {self.active_bot.pair} trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}"
                )
