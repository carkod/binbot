import logging
from typing import Type, Union
from urllib.error import HTTPError
from database.bot_crud import BotTableCrud
from database.models.bot_table import BotTable, PaperTradingTable
from database.paper_trading_crud import PaperTradingTableCrud
from tools.enum_definitions import CloseConditions, DealType, OrderSide, Strategy
from bots.models import BotModel, OrderModel, BotBase
from tools.enum_definitions import Status
from tools.exceptions import BinanceErrors, MarginShortError, BinbotErrors
from tools.round_numbers import (
    round_numbers,
    round_numbers_ceiling,
    round_timestamp,
)
from deals.factory import DealAbstract


class MarginDeal(DealAbstract):
    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ):
        super().__init__(bot, db_table)
        self.active_bot = bot
        self.db_table = db_table

    def get_remaining_assets(self) -> tuple[float, float]:
        """
        Get remaining isolated account assets
        given current isolated balance of isolated pair

        if account has borrowed assets yet, it should also return the amount borrowed

        """
        if float(self.isolated_balance[0]["quoteAsset"]["borrowed"]) > 0:
            self.active_bot.logs.append(
                f'Borrowed {self.isolated_balance[0]["quoteAsset"]["asset"]} still remaining, please clear out manually'
            )
            self.active_bot.status = Status.error
            self.controller.save(self.active_bot)

        if float(self.isolated_balance[0]["baseAsset"]["borrowed"]) > 0:
            self.active_bot.logs.append(
                f'Borrowed {self.isolated_balance[0]["baseAsset"]["asset"]} still remaining, please clear out manually'
            )
            self.active_bot.status = Status.error
            self.controller.save(self.active_bot)

        quote_asset = float(self.isolated_balance[0]["quoteAsset"]["free"])
        base_asset = float(self.isolated_balance[0]["baseAsset"]["free"])

        return round_numbers(quote_asset, self.qty_precision), round_numbers(
            base_asset, self.qty_precision
        )

    def cancel_open_orders(self, deal_type: DealType) -> BotModel:
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
                self.controller.update_logs(
                    "Old take profit order cancelled", self.active_bot
                )
            except HTTPError:
                self.controller.update_logs(
                    "Take profit order not found, no need to cancel", self.active_bot
                )
                return self.active_bot

            except BinanceErrors as error:
                # Most likely old error out of date orderId
                if error.code == -2011:
                    return self.active_bot

        return self.active_bot

    def terminate_failed_transactions(self) -> BotModel:
        """
        Transfer back from isolated account to spot account
        Disable isolated pair (so we don't reach the limit)
        """
        self.isolated_balance = self.get_isolated_balance(self.active_bot.pair)
        qty = self.isolated_balance[0]["quoteAsset"]["free"]
        self.transfer_isolated_margin_to_spot(
            asset=self.active_bot.fiat,
            symbol=self.active_bot.pair,
            amount=qty,
        )
        return self.active_bot

    def update_margin_orders(self) -> BotModel:
        """
        Keeps self.active_bot.orders up to date
        as they often don't fullfill immediately

        Used by streaming_controller
        """
        for order in self.active_bot.orders:
            if order.status != "FILLED":
                try:
                    self.cancel_margin_order(
                        symbol=self.active_bot.pair, order_id=order.order_id
                    )
                except HTTPError:
                    # No order to cancel
                    self.controller.update_logs(
                        f"Can't find order {order.order_id}", self.active_bot
                    )
                    pass

                if order.order_side == OrderSide.buy:
                    res = self.buy_margin_order(
                        symbol=self.active_bot.pair, qty=order.qty
                    )
                else:
                    res = self.sell_margin_order(
                        symbol=self.active_bot.pair, qty=order.qty
                    )

                # update with new order
                order.status = res["status"]
                order.price = float(res["price"])
                order.qty = float(res["origQty"])
                order.timestamp = int(res["transactTime"])
                order.order_id = int(res["orderId"])
                order.deal_type = order.deal_type
                order.order_type = res["type"]
                order.time_in_force = res["timeInForce"]
                order.order_side = res["side"]
                order.pair = res["symbol"]

                # update deal
                self.active_bot.deal.opening_qty = float(res["origQty"])
                self.active_bot.deal.opening_timestamp = int(res["transactTime"])
                self.active_bot.deal.opening_price = float(res["price"])

                self.controller.save(self.active_bot)

        return self.active_bot

    def init_margin_short(self, initial_price: float) -> BotModel:
        """
        Pre-tasks for bots that use margin_short strategy
        These tasks are not necessary for paper_trading

        1. transfer funds
        2. create loan with qty given by market
        3. borrow 2.5x to do base order
        """
        self.controller.update_logs(
            "Initializating margin_short tasks", self.active_bot
        )
        # Check margin account balance first
        balance = float(self.isolated_balance[0]["quoteAsset"]["free"])
        asset = self.active_bot.pair.replace(self.active_bot.fiat, "")
        # always enable, it doesn't cause errors
        try:
            self.enable_isolated_margin_account(symbol=self.active_bot.pair)
            borrow_res = self.get_max_borrow(
                asset=asset, isolated_symbol=self.active_bot.pair
            )
            error_msg = f"Checking borrowable amount: {borrow_res['amount']} (amount), {borrow_res['borrowLimit']} (limit)"
            self.controller.update_logs(error_msg, self.active_bot)
        except BinanceErrors as error:
            self.controller.update_logs(error.message, self.active_bot)
            if error.code == -11001 or error.code == -3052:
                # Isolated margin account needs to be activated with a transfer
                self.transfer_spot_to_isolated_margin(
                    asset=self.active_bot.fiat,
                    symbol=self.active_bot.pair,
                    amount=1,
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
                    asset=self.active_bot.fiat,
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

        try:
            loan_created = self.create_margin_loan(
                asset=asset, symbol=self.active_bot.pair, amount=qty
            )
        except BinanceErrors as error:
            # System does not have enough money to lend
            # transfer back and left client know (raise exception again)
            if error.code == -3045:
                self.terminate_failed_transactions()
                raise BinanceErrors(error.message, error.code)

        self.active_bot.deal.margin_loan_id = int(loan_created["tranId"])
        # in this new data system there is only one field for qty
        # so loan_amount == opening_qty
        # that makes sense, because we want to sell what we borrowed
        self.active_bot.deal.opening_qty = float(qty)

        return self.active_bot

    def terminate_margin_short(self, buy_back_fiat: bool = True) -> BotModel:
        """

        Args:
        - buy_back_fiat. By default it will buy back USDC (sell asset and transform into USDC)

        In the case of reversal, we don't want to do this additional transaction, as it will incur
        in an additional cost. So this is added to skip that section

        1. Repay loan
        2. Exchange asset to quote asset (USDC)
        3. Transfer back to spot
        """
        self.controller.update_logs(
            f"Terminating margin_short {self.active_bot.pair} for real bots trading",
            self.active_bot,
        )

        # Check margin account balance first
        balance = float(self.isolated_balance[0]["quoteAsset"]["free"])
        asset = self.isolated_balance[0]["baseAsset"]["asset"]
        if balance > 0:
            # repay
            qty, free = self.compute_margin_buy_back()
            repay_amount = qty

            if self.active_bot.deal.margin_loan_id == 0:
                raise BinbotErrors("No loan found for this bot")

            # Repay and Borrow have different ids
            # Check first if there is a repay before repaying
            query_loan: dict = self.get_margin_loan_details(
                loan_id=self.active_bot.deal.margin_loan_id,
                symbol=self.active_bot.pair,
            )

            if (
                self.active_bot.deal.margin_repay_id == 0
                and float(query_loan["total"]) > 0
                and repay_amount > 0
            ):
                # Only supress trailling 0s, so that everything is paid
                amount = round_numbers_ceiling(repay_amount, self.qty_precision)
                try:
                    repay_data = self.repay_margin_loan(
                        asset=asset, symbol=self.active_bot.pair, amount=amount
                    )
                    self.active_bot.deal.margin_repay_id = int(repay_data["tranId"])
                    self.controller.save(self.active_bot)
                except BinanceErrors as error:
                    if error.code == -3041:
                        self.controller.update_logs(error.message)
                        pass
                    if error.code == -3015:
                        # false alarm
                        pass
                except Exception as error:
                    logging.error(error)
                    # Continue despite errors to avoid losses
                    # most likely it is still possible to update bot
                    pass

                interests_data = self.get_interest_history(
                    asset=asset, symbol=self.active_bot.pair
                )

                self.active_bot.deal.total_interests = interests_data["rows"][0][
                    "interest"
                ]

            else:
                self.controller.update_logs(
                    "Loan not found for this deal, or it's been repaid.",
                    self.active_bot,
                )

            # Get updated balance
            self.isolated_balance = self.get_isolated_balance(self.active_bot.pair)
            sell_back_qty = round_numbers(
                float(self.isolated_balance[0]["baseAsset"]["free"]),
                self.qty_precision,
            )

            if buy_back_fiat and sell_back_qty > 0:
                # Sell quote and get base asset (USDC)
                # In theory, we should sell self.active_bot.base_order
                # but this can be out of sync

                res = self.sell_margin_order(
                    symbol=self.active_bot.pair, qty=sell_back_qty
                )

                price = float(res["price"])
                if price == 0:
                    price = self.calculate_avg_price(res["fills"])

                sell_back_order = OrderModel(
                    timestamp=res["transactTime"],
                    deal_type=DealType.take_profit,
                    order_id=int(res["orderId"]),
                    pair=res["symbol"],
                    order_side=res["side"],
                    order_type=res["type"],
                    price=price,
                    qty=float(res["origQty"]),
                    time_in_force=res["timeInForce"],
                    status=res["status"],
                )

                self.active_bot.deal.total_commissions = (
                    self.calculate_total_commissions(res["fills"])
                )

                self.active_bot.orders.append(sell_back_order)
                self.active_bot.deal.closing_price = price
                self.active_bot.deal.closing_qty = float(res["origQty"])
                self.active_bot.deal.closing_timestamp = float(res["transactTime"])
                self.active_bot.logs.append("Margin_short bot repaid, deal completed.")

            # Order and deal section completed, back to bot level
            self.controller.save(self.active_bot)

            try:
                # get new balance
                self.isolated_balance = self.get_isolated_balance(self.active_bot.pair)
                if float(self.isolated_balance[0]["quoteAsset"]["free"]) != 0:
                    # transfer back to SPOT account
                    self.transfer_isolated_margin_to_spot(
                        asset=self.active_bot.fiat,
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
                self.controller.update_logs(error_msg, self.active_bot)
                return self.active_bot

            self.active_bot.status = Status.completed
            self.controller.update_logs(
                f"{self.active_bot.pair} ISOLATED margin funds transferred back to SPOT.",
                self.active_bot,
            )

        self.controller.save(self.active_bot)
        return self.active_bot

    def margin_short_base_order(self) -> BotModel:
        """
        Same functionality as usual base_order
        with a few more fields. This is used during open_deal

        1. Check margin account balance
        2. Carry on with usual base_order
        """
        initial_price = self.matching_engine(
            self.active_bot.pair, True, qty=self.active_bot.base_order_size
        )

        if isinstance(self.controller, BotTableCrud):
            self.init_margin_short(initial_price)
            # init_margin_short will set opening_qty
            order_res = self.sell_margin_order(
                symbol=self.active_bot.pair,
                qty=self.active_bot.deal.opening_qty,
            )
        else:
            order_res = self.simulate_margin_order(
                pair=self.active_bot, side=OrderSide.sell
            )

        price = float(order_res["price"])
        if price == 0:
            price = self.calculate_avg_price(order_res["fills"])

        order_data = OrderModel(
            timestamp=order_res["transactTime"],
            order_id=int(order_res["orderId"]),
            deal_type=DealType.base_order,
            pair=order_res["symbol"],
            order_side=order_res["side"],
            order_type=order_res["type"],
            price=price,
            qty=float(order_res["origQty"]),
            time_in_force=order_res["timeInForce"],
            status=order_res["status"],
        )

        self.active_bot.deal.total_commissions = self.calculate_total_commissions(
            order_res["fills"]
        )

        self.active_bot.orders.append(order_data)

        self.active_bot.deal.opening_timestamp = round_timestamp(
            order_res["transactTime"]
        )
        self.active_bot.deal.opening_price = price
        self.active_bot.deal.opening_qty = float(order_res["origQty"])

        # Activate bot
        self.active_bot.status = Status.active
        self.controller.save(self.active_bot)
        return self.active_bot

    def streaming_updates(self, close_price: float) -> BotModel:
        """
        Margin_short streaming updates
        """

        self.close_conditions(close_price)

        self.active_bot.deal.current_price = close_price

        # For orders that are status not FILLED
        self.update_margin_orders()

        if self.active_bot.deal.stop_loss_price == 0:
            self.active_bot.deal.stop_loss_price = (
                self.active_bot.deal.opening_price
                + (
                    self.active_bot.deal.opening_price
                    * (self.active_bot.stop_loss / 100)
                )
            )

        self.controller.save(self.active_bot)

        if (
            close_price > 0
            and self.active_bot.trailling
            and self.active_bot.trailling_profit > 0
            and self.active_bot.trailling_deviation > 0
        ):
            # Direction 1.1: downward trend (short)
            # Breaking trailling
            # Trailling only to update when it's above opening_price
            if close_price < self.active_bot.deal.trailling_profit_price:
                self.update_trailling_profit(close_price)

            # Direction 2: upward trend (short). breaking the trailling_stop_loss
            # Make sure it's red candlestick, to avoid slippage loss
            # Sell after hitting trailling stop_loss and if price already broken trailling
            if close_price > self.active_bot.deal.trailling_stop_loss_price:
                self.controller.update_logs(
                    f"Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Selling {self.active_bot.pair}",
                    self.active_bot,
                )
                # since price is given by matching engine
                self.execute_take_profit()
                self.base_producer.update_required(
                    self.producer, "EXECUTE_MARGIN_TRAILLING_PROFIT"
                )

            # Direction 1.3: upward trend (short)
            # Breaking trailling_stop_loss, completing trailling
            if close_price > self.active_bot.deal.stop_loss_price:
                self.controller.update_logs(
                    f"Executing margin_short stop_loss reversal after hitting stop_loss_price {self.active_bot.deal.stop_loss_price}"
                )
                self.execute_stop_loss()
                self.base_producer.update_required(
                    self.producer, "EXECUTE_MARGIN_STOP_LOSS"
                )
                if self.active_bot.margin_short_reversal:
                    self.switch_to_long_bot()
                    self.base_producer.update_required(
                        self.producer, "EXECUTE_MARGIN_SWITCH_TO_LONG"
                    )

        if not self.active_bot.trailling and self.active_bot.deal.take_profit_price > 0:
            # Not a trailling bot, just simple take profit
            if close_price <= self.active_bot.deal.take_profit_price:
                self.controller.update_logs(
                    f"Executing margin_short take_profit after hitting take_profit_price {self.active_bot.deal.take_profit_price}"
                )
                self.execute_take_profit()
                self.base_producer.update_required(
                    self.producer, "EXECUTE_MARGIN_TAKE_PROFIT"
                )

        return self.active_bot

    def set_margin_take_profit(self) -> BotModel:
        """
        Sets take_profit for margin_short at initial activation
        """
        price = float(self.active_bot.deal.closing_price)
        if (
            hasattr(self.active_bot, "take_profit")
            and float(self.active_bot.take_profit) > 0
        ):
            take_profit_price = price - (
                price * (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price

        return self.active_bot

    def execute_stop_loss(self) -> BotModel:
        """
        Execute stop loss when price is hit
        This is used during streaming updates
        """
        # Margin buy (buy back)
        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.simulate_margin_order(
                self.active_bot.deal.opening_qty, OrderSide.buy
            )
        else:
            res = self.margin_liquidation(self.active_bot.pair)

        price = float(res["price"])
        if price == 0:
            price = self.calculate_avg_price(res["fills"])

        if res:
            stop_loss_order = OrderModel(
                timestamp=int(res["transactTime"]),
                deal_type=DealType.stop_loss,
                order_id=int(res["orderId"]),
                pair=res["symbol"],
                order_side=res["side"],
                order_type=res["type"],
                price=price,
                qty=float(res["origQty"]),
                time_in_force=res["timeInForce"],
                status=res["status"],
            )

            self.active_bot.deal.total_commissions = self.calculate_total_commissions(
                res["fills"]
            )

            self.active_bot.orders.append(stop_loss_order)

            self.active_bot.deal.closing_price = price
            self.active_bot.deal.closing_qty = float(res["origQty"])
            self.active_bot.deal.closing_timestamp = float(res["transactTime"])

            self.active_bot.logs.append("Completed Stop loss order")
            self.active_bot.status = Status.completed
        else:
            self.active_bot.logs.append("Unable to complete stop loss")

        self.controller.save(self.active_bot)

        return self.active_bot

    def execute_take_profit(self) -> BotModel:
        """
        Execute take profit when price is hit.
        This can be a simple take_profit order when take_profit_price is hit or
        a trailling_stop_loss when trailling_stop_loss_price is hit.
        This is because the only difference is the price and the price either provided
        by whatever triggers this sell or if not provided the matching_engine will provide it.

        This also sits well with the concept of "taking profit", which is closing a position at profit.

        - Buy back asset sold
        """
        if isinstance(self.controller, BotTableCrud):
            try:
                self.cancel_open_orders(DealType.take_profit)
            except Exception:
                # Regardless opened orders or not continue
                pass

        # Margin buy (buy back)
        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.simulate_margin_order(
                self.active_bot.deal.opening_qty, OrderSide.buy
            )
        else:
            self.controller.update_logs("Attempting to liquidate loan", self.active_bot)
            try:
                res = self.margin_liquidation(self.active_bot.pair)
            except BinanceErrors as error:
                self.active_bot.logs.append(error.message)
                self.active_bot.status = Status.error
                self.controller.save(self.active_bot)
                return self.active_bot

        if res:

            price = float(res["price"])
            if price == 0:
                price = self.calculate_avg_price(res["fills"])

            # No res means it wasn't properly closed/completed
            take_profit_order = OrderModel(
                timestamp=res["transactTime"],
                deal_type=DealType.take_profit,
                order_id=int(res["orderId"]),
                pair=res["symbol"],
                order_side=res["side"],
                order_type=res["type"],
                price=price,
                qty=float(res["origQty"]),
                time_in_force=res["timeInForce"],
                status=res["status"],
            )

            self.active_bot.deal.total_commissions = self.calculate_total_commissions(
                res["fills"]
            )

            self.active_bot.orders.append(take_profit_order)
            self.active_bot.deal.closing_price = price
            self.active_bot.deal.closing_timestamp = round_timestamp(
                res["transactTime"]
            )
            self.active_bot.deal.closing_qty = float(res["origQty"])
            self.active_bot.logs.append("Completed Take profit!")
            self.active_bot.status = Status.completed

        else:
            self.active_bot.logs.append("Unable to complete take profit")

        self.controller.save(self.active_bot)

        return self.active_bot

    def switch_to_long_bot(self) -> BotModel:
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
        self.controller.update_logs(
            "Switching margin_short to long strategy", self.active_bot
        )

        # Create new bot as you'd do through Dashboard terminal
        new_bot = BotBase.model_validate(self.active_bot.model_dump())
        new_bot.strategy = Strategy.long
        new_bot.status = Status.inactive
        new_bot.logs = []
        created_bot = self.controller.create(new_bot)

        # to avoid circular imports make network request
        # This class is already imported for switch_to_margin_short
        bot_id = self.request(
            url=self.bb_activate_bot_url, payload={"id": str(created_bot.id)}
        )
        self.controller.update_logs(
            f"Switched margin_short to long strategy. New bot id: {bot_id}"
        )
        return self.active_bot

    def update_trailling_profit(self, close_price: float) -> BotModel:
        # Direction 1: downward trend (short)
        if self.active_bot.deal.trailling_stop_loss_price == 0:
            price = (
                close_price
                if close_price < self.active_bot.deal.opening_price
                else self.active_bot.deal.opening_price
            )
            trailling_take_profit = price - (
                price * ((self.active_bot.take_profit) / 100)
            )
            stop_loss_trailling_price = trailling_take_profit - (
                trailling_take_profit * ((self.active_bot.trailling_deviation) / 100)
            )
            # If trailling_stop_loss is above (margin) the opening_price do not update trailling stop loss, because it'll close at a loss
            # stop_loss is the safe net in this case
            if stop_loss_trailling_price < self.active_bot.deal.opening_price:
                self.active_bot.deal.trailling_stop_loss_price = (
                    stop_loss_trailling_price
                )
                self.active_bot.logs.append(
                    f"{self.active_bot.pair} below opening_price, setting trailling_stop_loss (margin_short)"
                )
                self.controller.save(self.active_bot)

        # Keep trailling_stop_loss up to date
        if (
            self.active_bot.deal.trailling_stop_loss_price > 0
            and self.active_bot.deal.trailling_profit_price > 0
            and self.active_bot.deal.trailling_stop_loss_price
            < self.active_bot.deal.closing_price
        ):
            self.active_bot.deal.trailling_stop_loss_price = (
                self.active_bot.deal.trailling_profit_price
                * (1 + ((self.active_bot.trailling_deviation) / 100))
            )

            # Reset stop_loss_price to avoid confusion in front-end
            self.active_bot.deal.stop_loss_price = 0
            self.controller.update_logs(
                f"{self.active_bot.pair} Updating after broken first trailling_profit (short)",
                self.active_bot,
            )

        # Direction 1 (downward): breaking the current trailling
        if close_price <= self.active_bot.deal.trailling_profit_price:
            new_take_profit: float = close_price - (
                close_price * (self.active_bot.take_profit / 100)
            )
            new_trailling_stop_loss = close_price * (
                1 + (self.active_bot.trailling_deviation / 100)
            )
            # Update deal trailling profit
            self.active_bot.deal.trailling_profit_price = new_take_profit

            # Update trailling_stop_loss
            if new_trailling_stop_loss < self.active_bot.deal.closing_price:
                # Selling below buy_price will cause a loss
                # instead let it drop until it hits safety order or stop loss
                # Update trailling_stop_loss
                self.active_bot.deal.trailling_stop_loss_price = new_trailling_stop_loss

        self.controller.save(self.active_bot)

        return self.active_bot

    def close_conditions(self, current_price: float):
        """

        Check if there is a market reversal
        and close bot if so
        Get data from gainers and losers endpoint to analyze market trends
        """
        if self.active_bot.close_condition == CloseConditions.market_reversal:
            self.render_market_domination_reversal()
            if (
                self.market_domination_reversal
                and current_price > self.active_bot.deal.opening_price
            ):
                self.controller.update_logs(
                    f"Closing bot according to close_condition: {self.active_bot.close_condition}",
                    self.active_bot,
                )
                self.execute_stop_loss()
                self.base_producer.update_required(
                    self.producer, "EXECUTE_CLOSE_CONDITION_STOP_LOSS"
                )

        pass

    def close_all(self) -> BotModel:
        """
        Deactivation + liquidation of loans

        1. Close all orders if there any are still opened
        2. Terminate margin deal (repay loan, sell assets, transfer funds back to SPOT)
        3. Update bot status to completed
        """
        orders = self.active_bot.orders

        # Close all active orders
        if len(orders) > 0:
            for d in orders:
                if d.status == "NEW" or d.status == "PARTIALLY_FILLED":
                    self.controller.update_logs(
                        "Failed to close all active orders (status NEW), retrying...",
                        self.active_bot,
                    )
                    try:
                        self.cancel_margin_order(
                            symbol=self.active_bot.pair, order_id=d.order_id
                        )
                    except BinanceErrors:
                        break

        # Sell everything
        self.terminate_margin_short()

        return self.active_bot

    def open_deal(self) -> BotModel:
        """
        Bot activation requires:

        1. Opening a new deal, which entails opening orders
        2. Updating stop loss and take profit
        3. Updating trailling
        4. Save in db

        - If bot DOES have a base order, we still need to update stop loss and take profit and trailling
        """

        base_order_deal = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == DealType.base_order
            ),
            None,
        )

        if not base_order_deal:
            self.controller.update_logs(
                f"Opening new margin deal for {self.active_bot.pair}...",
                self.active_bot,
            )
            self.margin_short_base_order()

        self.active_bot = self.open_deal_trailling_parameters()
        self.base_producer.update_required(self.producer, "EXECUTE_MARGIN_OPEN_DEAL")
        return self.active_bot
