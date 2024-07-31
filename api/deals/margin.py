import logging

from time import time
from datetime import datetime
from urllib.error import HTTPError
from base_producer import BaseProducer
from tools.enum_definitions import CloseConditions, DealType, Strategy
from bots.schemas import BotSchema
from tools.enum_definitions import Status
from deals.base import BaseDeal
from deals.schema import MarginOrderSchema
from tools.exceptions import BinanceErrors, MarginShortError
from tools.round_numbers import round_numbers, supress_notation, round_numbers_ceiling


class MarginDeal(BaseDeal):
    def __init__(self, bot, db_collection_name) -> None:
        # Inherit from parent class
        super().__init__(bot, db_collection_name=db_collection_name)
        self.base_producer = BaseProducer()
        self.producer = self.base_producer.start_producer()

    def simulate_margin_order(self, qty, side):
        price = float(self.matching_engine(self.active_bot.pair, True, qty))
        order = {
            "symbol": self.active_bot.pair,
            "orderId": self.generate_id().int,
            "orderListId": -1,
            "clientOrderId": self.generate_id().hex,
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

    def get_remaining_assets(self) -> tuple[float, float]:
        """
        Get remaining isolated account assets
        given current isolated balance of isolated pair

        if account has borrowed assets yet, it should also return the amount borrowed

        """
        if float(self.isolated_balance[0]["quoteAsset"]["borrowed"]) > 0:
            self.update_deal_logs(
                f'Borrowed {self.isolated_balance[0]["quoteAsset"]["asset"]} still remaining, please clear out manually',
                self.active_bot
            )
            self.active_bot.status = Status.error

        if float(self.isolated_balance[0]["baseAsset"]["borrowed"]) > 0:
            self.update_deal_logs(
                f'Borrowed {self.isolated_balance[0]["baseAsset"]["asset"]} still remaining, please clear out manually',
                self.active_bot
            )
            self.active_bot.status = Status.error

        quote_asset = float(self.isolated_balance[0]["quoteAsset"]["free"])
        base_asset = float(self.isolated_balance[0]["baseAsset"]["free"])

        return round_numbers(quote_asset, self.qty_precision), round_numbers(
            base_asset, self.qty_precision
        )

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
                self.cancel_margin_order(symbol=self.active_bot.pair, order_id=order_id)
                self.update_deal_logs("Old take profit order cancelled", self.active_bot)
            except HTTPError as error:
                self.update_deal_logs("Take profit order not found, no need to cancel", self.active_bot)
                return

            except Exception as error:
                # Most likely old error out of date orderId
                if error.args[1] == -2011:
                    return

        return

    def terminate_failed_transactions(self):
        """
        Transfer back from isolated account to spot account
        Disable isolated pair (so we don't reach the limit)
        """
        self.isolated_balance = self.get_isolated_balance(self.active_bot.pair)
        qty = self.isolated_balance[0]["quoteAsset"]["free"]
        self.transfer_isolated_margin_to_spot(
            asset=self.active_bot.balance_to_use,
            symbol=self.active_bot.pair,
            amount=qty,
        )

    def init_margin_short(self, initial_price):
        """
        Pre-tasks for db_collection = bots
        These tasks are not necessary for paper_trading

        1. transfer funds
        2. create loan with qty given by market
        3. borrow 2.5x to do base order
        """
        self.update_deal_logs("Initializating margin_short tasks", self.active_bot)
        # Check margin account balance first
        balance = float(self.isolated_balance[0]["quoteAsset"]["free"])
        asset = self.active_bot.pair.replace(self.active_bot.balance_to_use, "")
        # always enable, it doesn't cause errors
        try:
            self.enable_isolated_margin_account(symbol=self.active_bot.pair)
            borrow_res = self.get_max_borrow(asset=asset, isolated_symbol=self.active_bot.pair)
            error_msg = f"Checking borrowable amount: {borrow_res['amount']} (amount), {borrow_res['borrowLimit']} (limit)"
            self.update_deal_logs(error_msg, self.active_bot)
        except BinanceErrors as error:
            self.update_deal_logs(error.message, self.active_bot)
            if error.code == -11001 or error.code == -3052:
                # Isolated margin account needs to be activated with a transfer
                self.transfer_spot_to_isolated_margin(
                    asset=self.active_bot.balance_to_use,
                    symbol=self.active_bot.pair,
                    amount="1",
                )

        # Given USDC amount we want to buy,
        # how much can we buy?
        qty = round_numbers_ceiling(
            (float(self.active_bot.base_order_size) / float(initial_price)),
            self.qty_precision,
        )

        # For leftover values
        # or transfers to activate isolated pair
        # sometimes to activate an isolated pair we need to transfer sth
        if balance <= 1:
            try:
                # transfer
                self.transfer_spot_to_isolated_margin(
                    asset=self.active_bot.balance_to_use,
                    symbol=self.active_bot.pair,
                    amount=self.active_bot.base_order_size,
                )
            except BinanceErrors as error:
                if error.code == -3041:
                    self.terminate_failed_transactions()
                    raise MarginShortError("Spot balance is not enough")
                if error.code == -11003:
                    self.terminate_failed_transactions()
                    raise MarginShortError("Isolated margin not available")

        self.create_margin_loan(
            asset=asset, symbol=self.active_bot.pair, amount=qty
        )
        loan_details = self.get_margin_loan_details(
            asset=asset, isolatedSymbol=self.active_bot.pair
        )

        self.active_bot.deal.margin_short_loan_principal = loan_details["rows"][0][
            "principal"
        ]
        self.active_bot.deal.margin_loan_id = loan_details["rows"][0]["txId"]

        # Estimate interest to add to total cost
        # This interest rate is much more accurate than any of the others
        hourly_fees = self.signed_request(
            url=self.isolated_hourly_interest,
            payload={"assets": asset, "isIsolated": "TRUE"},
        )
        self.active_bot.deal.hourly_interest_rate = float(
            hourly_fees[0]["nextHourlyInterestRate"]
        )
        self.active_bot.deal.margin_short_base_order = qty

        return

    def terminate_margin_short(self, buy_back_fiat: bool = True):
        """

        Args:
        - buy_back_fiat. By default it will buy back USDC (sell asset and transform into USDC)

        In the case of reversal, we don't want to do this additional transaction, as it will incur
        in an additional cost. So this is added to skip that section

        1. Repay loan
        2. Exchange asset to quote asset (USDC)
        3. Transfer back to spot
        """
        logging.info(
            f"Terminating margin_short {self.active_bot.pair} for real bots trading"
        )

        # Check margin account balance first
        balance = float(self.isolated_balance[0]["quoteAsset"]["free"])
        asset = float(self.isolated_balance[0]["baseAsset"]["asset"])       
        if balance > 0:
            # repay
            qty, free = self.compute_margin_buy_back(self.active_bot.pair, self.qty_precision)
            repay_amount = qty
            # Check if there is a loan
            # Binance may reject loans if they don't have asset
            # or binbot errors may transfer funds but no loan is created
            query_loan = self.signed_request(
                url=self.loan_record_url,
                payload={"asset": asset, "isolatedSymbol": self.active_bot.pair},
            )
            if query_loan["total"] > 0 and repay_amount > 0:
                # Only supress trailling 0s, so that everything is paid
                repay_amount = round_numbers_ceiling(repay_amount, self.qty_precision)
                try:
                    self.repay_margin_loan(
                        asset=asset,
                        symbol=self.active_bot.pair,
                        amount=repay_amount,
                        isIsolated="TRUE",
                    )
                except BinanceErrors as error:
                    if error.code == -3041:
                        self.active_bot.errors.append(error.message)
                        pass
                    if error.code == -3015:
                        # false alarm
                        pass
                except Exception as error:
                    self.update_deal_logs(error, self.active_bot)
                    # Continue despite errors to avoid losses
                    # most likely it is still possible to update bot
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

                self.isolated_balance = self.get_isolated_balance(self.active_bot.pair)
                sell_back_qty = supress_notation(
                    self.isolated_balance[0]["baseAsset"]["free"],
                    self.qty_precision,
                )

                if buy_back_fiat and float(sell_back_qty):
                    # Sell quote and get base asset (USDC)
                    # In theory, we should sell self.active_bot.base_order
                    # but this can be out of sync

                    res = self.sell_margin_order(
                        symbol=self.active_bot.pair, qty=sell_back_qty
                    )
                    sell_back_order = MarginOrderSchema(
                        timestamp=res["transactTime"],
                        deal_type=DealType.take_profit,
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
                    self.active_bot.deal.buy_total_qty = res["origQty"]
                    self.active_bot.status = Status.completed
                    self.active_bot.errors.append(
                        "Margin_short bot repaid, deal completed."
                    )

            else:
                self.active_bot.errors.append("Loan not found for this bot.")

            # Save in two steps, because it takes time for Binance to process repayments
            self.active_bot = self.save_bot_streaming(self.active_bot)

            try:
                # get new balance
                self.isolated_balance = self.get_isolated_balance(self.active_bot.pair)
                print(f"Transfering leftover isolated assets back to Spot")
                if float(self.isolated_balance[0]["quoteAsset"]["free"]) != 0:
                    # transfer back to SPOT account
                    self.transfer_isolated_margin_to_spot(
                        asset=self.active_bot.balance_to_use,
                        symbol=self.active_bot.pair,
                        amount=self.isolated_balance[0]["quoteAsset"]["free"],
                    )
                if float(self.isolated_balance[0]["baseAsset"]["free"]) != 0:
                    self.transfer_isolated_margin_to_spot(
                        asset=asset,
                        symbol=self.active_bot.pair,
                        amount=self.isolated_balance[0]["baseAsset"]["free"],
                    )
            except Exception as error:
                error_msg = f"Failed to transfer isolated assets to spot: {error}"
                logging.error(error_msg)
                self.active_bot.errors.append(error_msg)
                return

            completion_msg = f"{self.active_bot.pair} ISOLATED margin funds transferred back to SPOT."
            self.active_bot.status = Status.completed
            self.active_bot.errors.append(completion_msg)

        self.active_bot = self.save_bot_streaming(self.active_bot)
        return self.active_bot

    def margin_short_base_order(self):
        """
        Same functionality as usual base_order
        with a few more fields. This is used during open_deal

        1. Check margin account balance
        2. Carry on with usual base_order
        """
        initial_price = float(self.matching_engine(self.active_bot.pair, False))

        if self.db_collection.name == "bots":
            self.init_margin_short(initial_price)
            try:
                order_res = self.sell_margin_order(
                    symbol=self.active_bot.pair,
                    qty=self.active_bot.deal.margin_short_base_order,
                )
            except BinanceErrors as error:
                if error.code == -3052:
                    print(error)
                    return
        else:
            # Simulate Margin sell
            # qty doesn't matter in paper bots
            order_res = self.simulate_margin_order(1, "SELL")

        order_data = MarginOrderSchema(
            timestamp=order_res["transactTime"],
            order_id=order_res["orderId"],
            deal_type=DealType.base_order,
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

        self.close_conditions(float(close_price))

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

        # bugs, normally this should be set at deal opening
        if self.active_bot.deal.take_profit_price == 0:
            self.set_margin_take_profit()

        logging.debug(
            f"margin_short streaming updating {self.active_bot.pair} @ {self.active_bot.deal.stop_loss_price} and interests {self.active_bot.deal.margin_short_loan_interest}"
        )

        self.save_bot_streaming(self.active_bot)

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
                self.active_bot = self.save_bot_streaming(self.active_bot)

            else:
                # Execute the usual non-trailling take_profit
                self.update_deal_logs(f"Executing margin_short take_profit after hitting take_profit_price {self.active_bot.deal.stop_loss_price}", self.active_bot)
                self.execute_take_profit()
                self.base_producer.update_required(self.producer, self.active_bot.id, "EXECUTE_MARGIN_TAKE_PROFIT")

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
            self.execute_take_profit()
            self.base_producer.update_required(self.producer, self.active_bot.id, "EXECUTE_MARGIN_TRAILLING_PROFIT")

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
            self.base_producer.update_required(self.producer, self.active_bot.id, "EXECUTE_MARGIN_STOP_LOSS")
            if self.active_bot.margin_short_reversal:
                self.switch_to_long_bot()
                self.base_producer.update_required(self.producer, self.active_bot.id, "EXECUTE_MARGIN_SWITCH_TO_LONG")

            
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
        # Margin buy (buy back)
        if self.db_collection.name == "paper_trading":
            res = self.simulate_margin_order(self.active_bot.deal.buy_total_qty, "BUY")
        else:
            # Cancel orders first
            # paper_trading doesn't have real orders so no need to check
            self.cancel_open_orders(DealType.stop_loss)
            res = self.margin_liquidation(self.active_bot.pair, self.qty_precision)

        stop_loss_order = MarginOrderSchema(
            timestamp=res["transactTime"],
            deal_type=DealType.stop_loss,
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
        self.active_bot.status = Status.completed
        self.active_bot = self.save_bot_streaming(self.active_bot)

        return

    def execute_take_profit(self):
        """
        Execute take profit when price is hit.
        This can be a simple take_profit order when take_profit_price is hit or
        a trailling_stop_loss when trailling_stop_loss_price is hit.
        This is because the only difference is the price and the price either provided
        by whatever triggers this sell or if not provided the matching_engine will provide it.

        This also sits well with the concept of "taking profit", which is closing a position at profit.

        - Buy back asset sold
        """
        if self.db_collection.name == "bots":
            self.cancel_open_orders("take_profit")

        # Margin buy (buy back)
        if self.db_collection.name == "paper_trading":
            res = self.simulate_margin_order(self.active_bot.deal.buy_total_qty, "BUY")
        else:
            res = self.margin_liquidation(self.active_bot.pair, self.qty_precision)

        if res:
        # No res means it wasn't properly closed/completed

            take_profit_order = MarginOrderSchema(
                timestamp=res["transactTime"],
                deal_type=DealType.take_profit,
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
        
        else:
            msg = f"Re-completed take profit"
        
        self.active_bot.errors.append(msg)
        self.active_bot.status = Status.completed
        self.active_bot = self.save_bot_streaming(self.active_bot)

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
        self.update_deal_logs("Switching margin_short to long strategy", self.active_bot)
        self.active_bot.strategy = Strategy.long
        self.active_bot = self.create_new_bot_streaming(active_bot=self.active_bot)

        bot = self.base_order()
        self.active_bot = BotSchema(**bot)

        # Keep bot up to date in the DB
        # this avoid unsyched bots when errors ocurr in other functions
        self.active_bot = self.save_bot_streaming(self.active_bot)
        return self.active_bot

    def update_trailling_profit(self, close_price):
        # Fix potential bugs in bot updates
        if self.active_bot.deal.take_profit_price == 0:
            self.margin_short_base_order()
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
                self.active_bot = self.save_bot_streaming(self.active_bot)
                self.update_deal_logs(f"{self.active_bot.pair} Setting trailling_stop_loss (short) and saved to DB", self.active_bot)

        if self.active_bot.deal.trailling_profit_price == 0:
            # Current take profit + next take_profit
            trailling_price = float(self.active_bot.deal.take_profit_price) - (
                float(self.active_bot.deal.take_profit_price)
                * (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.trailling_profit_price = trailling_price
            logging.info(
                f"{self.active_bot.pair} Updated (Didn't break trailling), updating trailling price (short)"
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

            # Reset stop_loss_price to avoid confusion in front-end
            self.active_bot.deal.stop_loss_price = 0
            self.update_deal_logs(f"{self.active_bot.pair} Updating after broken first trailling_profit (short)", self.active_bot)

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
                    f"{datetime.now()} Updated {self.active_bot.pair} trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}"
                )

    
    def close_conditions(self, current_price):
        """

        Check if there is a market reversal
        and close bot if so
        Get data from gainers and losers endpoint to analyze market trends
        """
        if self.active_bot.close_condition == CloseConditions.market_reversal:
            self.render_market_domination_reversal()
            if self.market_domination_reversal and current_price > self.active_bot.deal.buy_price:
                self.update_deal_logs(f"Closing bot according to close_condition: {self.active_bot.close_condition}", self.active_bot)
                self.execute_stop_loss()
                self.base_producer(self.active_bot.id, "EXECUTE_CLOSE_CONDITION_STOP_LOSS")

        pass
