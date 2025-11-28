import logging

from typing import Type, Union
from urllib.error import HTTPError
from bots.models import BotBase, BotModel, OrderModel
from time import sleep
from databases.crud.bot_crud import BotTableCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from deals.abstractions.factory import DealAbstract
from tools.enum_definitions import (
    CloseConditions,
    DealType,
    OrderSide,
    QuoteAssets,
    Status,
    Strategy,
)
from tools.exceptions import BinanceErrors, MarginShortError
from tools.maths import (
    round_numbers,
    round_numbers_ceiling,
    round_numbers_floor,
    round_timestamp,
)
from databases.crud.symbols_crud import SymbolsCrud


class MarginDealAbstract(DealAbstract):
    """
    Store here utility functions, setters and getters
    to avoid making MarginDeal too big
    and decreases amount of code needed to read -
    for new tasks, you'd just create a new function here
    and call it from MarginDeal

    tip: write functions first in MarginDeal
    then move them to this
    if it's a reused utility function
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ):
        super().__init__(bot, db_table)
        self.active_bot = bot
        self.db_table = db_table
        self.symbols_crud = SymbolsCrud()
        self.isolated_balance = self.api.get_isolated_balance(self.active_bot.pair)

    """
    Reusable utility functions
    """

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
                self.api.cancel_margin_order(
                    symbol=self.active_bot.pair, order_id=order_id
                )
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
        self.isolated_balance = self.api.get_isolated_balance(self.active_bot.pair)
        qty = self.isolated_balance[0]["quoteAsset"]["free"]
        self.api.transfer_isolated_margin_to_spot(
            asset=self.active_bot.fiat,
            symbol=self.active_bot.pair,
            amount=qty,
        )
        return self.active_bot

    def margin_short_base_order(self, repurchase_multiplier: float = 0.95) -> BotModel:
        """
        Same functionality as usual base_order
        with a few more fields. This is used during open_deal

        1. Check margin account balance
        2. Carry on with usual base_order
        """

        if self.active_bot.quote_asset != QuoteAssets.USDC:
            response = self.check_available_balance()
            if response:
                order = OrderModel(
                    timestamp=int(response["transactTime"]),
                    order_id=int(response["orderId"]),
                    deal_type=DealType.conversion,
                    pair=response["symbol"],
                    order_side=response["side"],
                    order_type=response["type"],
                    price=float(response["price"]),
                    qty=float(response["origQty"]),
                    time_in_force=response["timeInForce"],
                    status=response["status"],
                )
                self.active_bot.orders.append(order)
                self.controller.update_logs(
                    bot=self.active_bot, log_message="Quote asset purchase successful."
                )
                self.active_bot.deal.base_order_size = float(response["origQty"])
                # give some time for order to complete
                sleep(3)

            # Long position does not need qty in take_profit
            # initial price with 1 qty should return first match
            # also use always last_ticker_price rather than book depth
            # because bid/ask prices wicks can go way out of the candle
            last_ticker_price = self.api.last_ticker_price(self.active_bot.pair)

            # Use all available quote asset balance
            # this avoids diffs in ups and downs in prices and fees
            available_quote_asset = self.order.get_single_raw_balance(
                self.active_bot.quote_asset
            )
            qty = round_numbers_floor(
                (available_quote_asset / last_ticker_price),
                self.qty_precision,
            )
        else:
            self.active_bot.deal.base_order_size = self.active_bot.fiat_order_size
            last_ticker_price = self.api.last_ticker_price(self.active_bot.pair)
            qty = round_numbers_floor(
                (self.active_bot.deal.base_order_size / last_ticker_price),
                self.qty_precision,
            )

        if isinstance(self.controller, PaperTradingTableCrud):
            order_res = self.order.simulate_margin_order(
                pair=self.active_bot.pair, side=OrderSide.sell
            )

        else:
            self.init_margin_short(last_ticker_price)
            try:
                # init_margin_short will set opening_qty
                order_res = self.order.sell_margin_order(
                    symbol=self.active_bot.pair,
                    qty=(qty * repurchase_multiplier),
                )
            except BinanceErrors as error:
                if error.code == -2010:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message="Base asset purchase failed! Not enough funds.",
                    )
                    if repurchase_multiplier > 0.80:
                        self.margin_short_base_order(
                            repurchase_multiplier=repurchase_multiplier - 0.05
                        )
                    return self.active_bot

        self.controller.update_logs(
            bot=self.active_bot, log_message="Base order executed."
        )

        price = float(order_res["price"])
        if self.active_bot.deal.base_order_size == 0:
            self.active_bot.deal.base_order_size = float(order_res["origQty"]) * price

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

        self.active_bot.deal.total_commissions += order_res["commissions"]

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

    def short_update_deal_trailling_parameters(self) -> BotModel:
        """
        Same as open_deal_trailling_parameters
        but for updating when deal is already activated

        This makes sure deal trailling values are up to date and
        not out of sync with the bot parameters
        """

        if self.active_bot.strategy == Strategy.margin_short:
            logging.error("Bot executing wrong short_update_deal_trailling_parameters")
            return self.active_bot

        if self.active_bot.deal.stop_loss_price == 0:
            self.active_bot.deal.stop_loss_price = (
                self.active_bot.deal.opening_price
                + (
                    self.active_bot.deal.opening_price
                    * (self.active_bot.stop_loss / 100)
                )
            )

        if self.active_bot.trailling:
            price = self.active_bot.deal.opening_price
            if self.active_bot.deal.trailling_profit_price == 0:
                trailling_profit = price - (
                    price * (self.active_bot.trailling_profit / 100)
                )
                self.active_bot.deal.trailling_profit_price = round_numbers(
                    trailling_profit, self.price_precision
                )

            if self.active_bot.deal.trailling_stop_loss_price == 0:
                trailling_stop_loss = price + (
                    price * (self.active_bot.trailling_deviation / 100)
                )
                self.active_bot.deal.trailling_stop_loss_price = round_numbers(
                    trailling_stop_loss, self.price_precision
                )
        return self.active_bot

    def short_open_deal_trailling_parameters(self) -> BotModel:
        """
        Updates stop loss and trailling paramaters for deal
        during deal opening.

        Only use for short margin strategy!
        """

        if self.active_bot.strategy == Strategy.long:
            logging.error("Bot executing wrong short_open_deal_trailling_parameters")
            return self.active_bot

        # Update stop loss regarless of base order
        if self.active_bot.stop_loss > 0:
            price = self.active_bot.deal.opening_price
            self.active_bot.deal.stop_loss_price = price + (
                price * (self.active_bot.stop_loss / 100)
            )

        # Bot has only take_profit set
        if not self.active_bot.trailling and self.active_bot.take_profit > 0:
            price = self.active_bot.deal.opening_price
            take_profit_price = price - (price * (self.active_bot.take_profit) / 100)
            self.active_bot.deal.take_profit_price = round_numbers(
                take_profit_price, self.price_precision
            )

        # Bot has trailling set
        # trailling_profit must also be set
        if self.active_bot.trailling:
            if self.active_bot.strategy == Strategy.margin_short:
                price = self.active_bot.deal.opening_price
                trailling_profit = price - (
                    price * (self.active_bot.trailling_profit / 100)
                )
                self.active_bot.deal.trailling_profit_price = round_numbers(
                    trailling_profit, self.price_precision
                )
                # do not set trailling_stop_loss_price until trailling_profit_price is broken
            else:
                price = self.active_bot.deal.opening_price
                trailling_profit = price + (
                    price * (self.active_bot.trailling_profit / 100)
                )
                self.active_bot.deal.trailling_profit_price = round_numbers(
                    trailling_profit, self.price_precision
                )
                # do not set trailling_stop_loss_price until trailling_profit_price is broken

        if self.active_bot.status == Status.inactive:
            self.active_bot.add_log("Bot activated")
        else:
            self.active_bot.add_log("Bot deal updated")

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
        balance = 0.0
        if len(self.isolated_balance) > 0:
            # Check margin account balance first
            balance = float(self.isolated_balance[0]["quoteAsset"]["free"])

        asset = self.active_bot.pair.replace(self.active_bot.fiat, "")
        # always enable, it doesn't cause errors
        try:
            self.api.enable_isolated_margin_account(symbol=self.active_bot.pair)
            borrow_res = self.api.get_max_borrow(
                asset=asset, isolated_symbol=self.active_bot.pair
            )
            error_msg = f"Checking borrowable amount: {borrow_res['amount']} (amount), {borrow_res['borrowLimit']} (limit)"
            self.controller.update_logs(error_msg, self.active_bot)
        except BinanceErrors as error:
            self.controller.update_logs(error.message, self.active_bot)
            if error.code == -11001 or error.code == -3052:
                # Isolated margin account needs to be activated with a transfer
                self.api.transfer_spot_to_isolated_margin(
                    asset=self.active_bot.fiat,
                    symbol=self.active_bot.pair,
                    amount=1,
                )
                self.api.enable_isolated_margin_account(symbol=self.active_bot.pair)
                pass

        # Given USDC amount we want to buy,
        # how much can we buy?
        qty = round_numbers_ceiling(
            (float(self.active_bot.deal.base_order_size) / float(initial_price)),
            self.qty_precision,
        )

        # For leftover values
        # or transfers to activate isolated pair
        # sometimes to activate an isolated pair we need to transfer sth
        if balance <= 1:
            try:
                # transfer
                self.api.transfer_spot_to_isolated_margin(
                    asset=self.active_bot.fiat,
                    symbol=self.active_bot.pair,
                    amount=self.active_bot.deal.base_order_size,
                )
            except BinanceErrors as error:
                self.controller.update_logs(error.message, self.active_bot)
                if error.code == -3041:
                    self.terminate_failed_transactions()
                    raise MarginShortError("Spot balance is not enough")
                if error.code == -11003:
                    self.terminate_failed_transactions()
                    raise MarginShortError("Isolated margin not available")

        try:
            loan_created = self.api.create_margin_loan(
                asset=asset, symbol=self.active_bot.pair, amount=qty
            )
            self.controller.update_logs("Loan created", self.active_bot)
        except BinanceErrors as error:
            # System does not have enough money to lend
            # transfer back and left client know (raise exception again)
            if error.code == -3045:
                self.controller.update_logs(error.message, self.active_bot)
                self.terminate_failed_transactions()
                raise BinanceErrors(error.message, error.code)

        self.active_bot.deal.margin_loan_id = int(loan_created["tranId"])
        # in this new data system there is only one field for qty
        # so loan_amount == opening_qty
        # that makes sense, because we want to sell what we borrowed
        self.active_bot.deal.opening_qty = float(qty)

        return self.active_bot

    def execute_stop_loss(self) -> BotModel:
        """
        Execute stop loss when price is hit
        This is used during streaming updates
        """
        # Margin buy (buy back)
        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.order.simulate_margin_order(
                self.active_bot.deal.opening_qty, OrderSide.buy
            )
        else:
            res = self.margin_liquidation(self.active_bot.pair)

        price = float(res["price"])

        if "code" in res:
            self.active_bot.add_log(f"Unable to complete stop loss {res['msg']}")
            return self.active_bot

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

        self.active_bot.deal.total_commissions += res["commissions"]

        self.active_bot.orders.append(stop_loss_order)

        self.active_bot.deal.closing_price = price
        self.active_bot.deal.closing_qty = float(res["origQty"])
        self.active_bot.deal.closing_timestamp = round_timestamp(res["transactTime"])

        self.active_bot.status = Status.completed
        self.active_bot.add_log("Completed Stop loss order")

        self.controller.save(self.active_bot)

        self.sell_quote_asset()
        return self.active_bot

    def execute_take_profit(
        self, take_profit_type: DealType = DealType.take_profit
    ) -> BotModel:
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
                self.cancel_open_orders(take_profit_type)
            except Exception:
                # Regardless opened orders or not continue
                pass

        # Margin buy (buy back)
        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.order.simulate_margin_order(
                self.active_bot.deal.opening_qty, OrderSide.buy
            )
        else:
            self.controller.update_logs("Attempting to liquidate loan", self.active_bot)
            try:
                res = self.margin_liquidation(self.active_bot.pair)
            except BinanceErrors as error:
                self.active_bot.add_log(error.message)
                self.active_bot.status = Status.error
                self.controller.save(self.active_bot)
                return self.active_bot

        if res:
            price = float(res["price"])
            # No res means it wasn't properly closed/completed
            take_profit_order = OrderModel(
                timestamp=res["transactTime"],
                deal_type=take_profit_type,
                order_id=int(res["orderId"]),
                pair=res["symbol"],
                order_side=res["side"],
                order_type=res["type"],
                price=price,
                qty=float(res["origQty"]),
                time_in_force=res["timeInForce"],
                status=res["status"],
            )

            self.active_bot.deal.total_commissions += res["commissions"]

            self.active_bot.orders.append(take_profit_order)
            self.active_bot.deal.closing_price = price
            self.active_bot.deal.closing_timestamp = round_timestamp(
                res["transactTime"]
            )
            self.active_bot.deal.closing_qty = float(res["origQty"])
            self.active_bot.add_log("Completed Take profit!")
            self.active_bot.status = Status.completed

        else:
            self.active_bot.add_log("Unable to complete take profit")

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
        new_bot.logs = []

        # margin bot fund liquidation and network request can cause
        # failure of the bot creation
        # so set status to active to be able to open_deal again
        new_bot.status = Status.active

        # Create new bot
        created_bot = self.controller.create(new_bot)

        url = self.binbot_api.bb_activate_bot_url
        if isinstance(self.controller, PaperTradingTableCrud):
            url = self.binbot_api.bb_paper_trading_activate_url

        # to avoid circular imports make network request
        # This class is already imported for switch_to_margin_short
        bot_id = self.binbot_api.request(url=url, payload={"id": str(created_bot.id)})
        self.controller.update_logs(
            f"Switched margin_short to long strategy. New bot id: {bot_id}",
            self.active_bot,
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
                self.active_bot.add_log(
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
            if (
                self.market_domination_reversal
                and current_price > self.active_bot.deal.opening_price
            ):
                self.controller.update_logs(
                    f"Closing bot according to close_condition: {self.active_bot.close_condition}",
                    self.active_bot,
                )
                self.execute_stop_loss()

        pass
