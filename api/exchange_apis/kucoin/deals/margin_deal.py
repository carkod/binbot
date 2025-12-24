import logging
from typing import Type, Union, Tuple
from tools.maths import (
    round_numbers_floor,
    round_timestamp,
    round_numbers,
    round_numbers_ceiling,
)
from databases.crud.symbols_crud import SymbolsCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from bots.models import BotModel, OrderModel
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.bot_crud import BotTableCrud
from exchange_apis.kucoin.deals.base import KucoinBaseBalance
from tools.enum_definitions import DealType, OrderStatus, Strategy, QuoteAssets, Status
from kucoin_universal_sdk.generate.spot.order.model_get_order_by_order_id_resp import (
    GetOrderByOrderIdResp,
)
from time import sleep
from kucoin_universal_sdk.generate.margin.order.model_add_order_req import (
    AddOrderReq,
)
from kucoin_universal_sdk.generate.account.account.model_get_isolated_margin_account_resp import (
    GetIsolatedMarginAccountAssets,
)
from tools.exceptions import MarginLoanNotFound


class KucoinMarginDeal(KucoinBaseBalance):
    """Stub KuCoin margin deal implementation matching Binance margin deal interface.

    Provides method signatures for polymorphic delegation; implementations pending.
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ) -> None:
        super().__init__()
        self.active_bot = bot
        self.db_table = db_table
        self.symbols_crud = SymbolsCrud()
        # Provide controller attribute for parity with Binance implementations
        self.controller: Union[PaperTradingTableCrud, BotTableCrud]
        if db_table == PaperTradingTable:
            self.controller = PaperTradingTableCrud()
        else:
            self.controller = BotTableCrud()
        self.symbol_info = SymbolsCrud().get_symbol(bot.pair)
        self.price_precision = self.symbol_info.price_precision
        self.qty_precision = self.symbol_info.qty_precision
        self.symbol = self.get_symbol(bot.pair, bot.quote_asset)

    def get_isolated_balance(self) -> GetIsolatedMarginAccountAssets | None:
        symbol = self.get_symbol(self.active_bot.pair, self.active_bot.quote_asset)
        result = self.kucoin_api.get_isolated_balance(symbol=symbol)
        if result and len(result.assets) > 0:
            return result.assets[0]
        return None

    def buy_order_with_available_balance(
        self,
    ) -> GetOrderByOrderIdResp | None:
        """
        Combines buy_order and balance checks
        encapuslates common logic
        """
        balance = self.get_isolated_balance()
        if balance:
            available_balance = balance.quote_asset.available
            last_ticker_price = self.kucoin_api.get_ticker_price(self.symbol)
            qty = round_numbers_floor(
                (available_balance / last_ticker_price),
                self.qty_precision,
            )

            order = self.kucoin_api.buy_margin_order(
                symbol=self.symbol,
                qty=qty,
            )
            return order
        return None

    def compute_margin_buy_back(self) -> Tuple[float | int, float | int]:
        """
        Same as compute_qty but with isolated margin balance

        Find available amount to buy_back
        this is the borrowed amount + interests.
        Decimals have to be rounded up to avoid leaving
        "leftover" interests
        """
        qty: float = 0
        free: float = 0
        balance = self.get_isolated_balance()

        if (
            not balance
            or balance.quote_asset.available == 0
            or balance.base_asset.liability == 0
        ):
            return qty, free

        qty = float(balance.base_asset.liability) + float(
            balance.base_asset.liability_interest
        )

        qty = round_numbers_ceiling(qty, self.qty_precision)
        free = float(balance.base_asset.available)
        return qty, free

    def margin_liquidation(self) -> GetOrderByOrderIdResp:
        """
        Emulate Binance Dashboard One click liquidation function

        Args:
        - pair: a.k.a symbol, quote asset + base asset
        - qty_precision: to round numbers for Binance  Passed optionally to
        reduce number of requests to avoid rate limit.
        """
        balance = self.get_isolated_balance()
        if not balance:
            raise MarginLoanNotFound("Isolated margin balance not found")

        base = balance.base_asset.total
        quote = balance.quote_asset.total
        # Check margin account balance first
        borrowed_amount = float(balance.base_asset.liability)
        free = float(balance.base_asset.available)
        system_order = None

        if borrowed_amount > 0:
            # repay_amount contains total borrowed_amount + interests + commissions for buying back
            # borrow amount is only the loan
            repay_amount, free = self.compute_margin_buy_back()

            if free == 0 or free < repay_amount:
                qty = round_numbers_ceiling(repay_amount - free, self.qty_precision)
                system_order = self.kucoin_api.buy_margin_order(
                    symbol=self.symbol,
                    qty=qty,
                )
                repay_amount, free = self.compute_margin_buy_back()
            else:
                msg = "Unable to match isolated balance with repay amount"
                self.controller.update_logs(msg, self.active_bot)
                raise MarginLoanNotFound(msg)

            self.kucoin_api.repay_margin_loan(
                asset=self.active_bot.quote_asset,
                symbol=self.symbol,
                amount=repay_amount,
            )

            # get new balance
            balance = self.get_isolated_balance()

        if balance and float(balance.quote_asset.available) != 0:
            # transfer back to SPOT account
            self.kucoin_api.transfer_isolated_margin_to_spot(
                asset=quote,
                symbol=self.symbol,
                amount=balance.quote_asset.available,
            )
        if balance and float(balance.base_asset.available) != 0:
            self.kucoin_api.transfer_isolated_margin_to_spot(
                asset=base,
                symbol=self.symbol,
                amount=balance.base_asset.available,
            )

        if borrowed_amount == 0:
            # Funds are transferred back by now,
            # disabling pair should be done by cronjob,
            # therefore no reason not to complete the bot
            self.active_bot.status = Status.completed

            raise MarginLoanNotFound("Isolated margin loan already liquidated")

        return system_order

    def margin_short_base_order(self, repurchase_multiplier: float = 0.95) -> BotModel:
        """
        Same functionality as usual base_order
        with a few more fields. This is used during open_deal

        1. Check margin account balance
        2. Carry on with usual base_order
        """
        balance = self.get_isolated_balance()

        if not balance:
            self.controller.update_logs(
                "Isolated margin balance not found", self.active_bot
            )
            return self.active_bot

        if self.active_bot.quote_asset != QuoteAssets.USDC:
            system_order = self.buy_order_with_available_balance()
            if system_order:
                order = OrderModel(
                    timestamp=system_order.created_at,
                    order_id=int(system_order.id),
                    deal_type=DealType.conversion,
                    pair=system_order.symbol,
                    order_side=system_order.side,
                    order_type=system_order.type,
                    price=float(system_order.price),
                    qty=float(system_order.size),
                    time_in_force=system_order.time_in_force,
                    status=OrderStatus.FILLED
                    if system_order.active
                    else OrderStatus.EXPIRED,
                )
                self.active_bot.orders.append(order)
                self.controller.update_logs(
                    bot=self.active_bot, log_message="Quote asset purchase successful."
                )
                self.active_bot.deal.base_order_size = float(system_order.size)
                # give some time for order to complete
                sleep(3)

            # Long position does not need qty in take_profit
            # initial price with 1 qty should return first match
            # also use always last_ticker_price rather than book depth
            # because bid/ask prices wicks can go way out of the candle
            last_ticker_price = self.kucoin_api.get_ticker_price(self.symbol)

            # Use all available quote asset balance
            # this avoids diffs in ups and downs in prices and fees
            available_quote_asset = balance.quote_asset.available
            qty = available_quote_asset / last_ticker_price
        else:
            self.active_bot.deal.base_order_size = self.active_bot.fiat_order_size
            last_ticker_price = self.kucoin_api.get_ticker_price(self.symbol)
            qty = round_numbers_floor(
                (self.active_bot.deal.base_order_size / last_ticker_price),
                self.qty_precision,
            )

        if isinstance(self.controller, PaperTradingTableCrud):
            system_order = self.kucoin_api.simulate_margin_order(
                symbol=self.symbol, side=AddOrderReq.SideEnum.SELL, qty=qty
            )

        else:
            self.init_margin_short(last_ticker_price)
            # init_margin_short will set opening_qty
            system_order = self.kucoin_api.sell_margin_order(
                symbol=self.symbol,
                qty=(qty * repurchase_multiplier),
            )

        self.controller.update_logs(
            bot=self.active_bot, log_message="Base order executed."
        )

        price = float(system_order.price)

        if self.active_bot.deal.base_order_size == 0:
            self.active_bot.deal.base_order_size = float(system_order.size) * price

        order_data = OrderModel(
            timestamp=system_order.created_at,
            order_id=int(system_order.id),
            deal_type=DealType.base_order,
            pair=system_order.symbol,
            order_side=system_order.side,
            order_type=system_order.type,
            price=price,
            qty=float(system_order.size),
            time_in_force=system_order.time_in_force,
            status=OrderStatus.FILLED if system_order.active else OrderStatus.EXPIRED,
        )

        self.active_bot.deal.total_commissions += float(system_order.fee)
        self.active_bot.orders.append(order_data)

        self.active_bot.deal.opening_timestamp = round_timestamp(
            system_order.created_at
        )
        self.active_bot.deal.opening_price = price
        self.active_bot.deal.opening_qty = float(system_order.size)
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
        balance = self.get_isolated_balance()

        # For leftover values
        # or transfers to activate isolated pair
        # sometimes to activate an isolated pair we need to transfer sth
        if balance:
            self.kucoin_api.transfer_spot_to_isolated_margin(
                asset=self.active_bot.fiat,
                symbol=self.symbol,
                amount=self.active_bot.deal.base_order_size,
            )
        # Given USDT amount we want to buy,
        # how much can we buy?
        qty = round_numbers_ceiling(
            (float(self.active_bot.deal.base_order_size) / float(initial_price)),
            self.qty_precision,
        )

        loan_created = self.kucoin_api.create_margin_loan(
            asset=self.active_bot.quote_asset, symbol=self.symbol, amount=qty
        )
        self.controller.update_logs("Loan created", self.active_bot)

        self.active_bot.deal.margin_loan_id = int(loan_created.order_no)
        # in this new data system there is only one field for qty
        # so loan_amount == opening_qty
        # that makes sense, because we want to sell what we borrowed
        self.active_bot.deal.opening_qty = float(loan_created.actual_size)

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
            if not self.symbol_info.is_margin_trading_allowed:
                self.active_bot.margin_short_reversal = False
                self.controller.update_logs(
                    f"Disabled auto long bot reversal. Exchange doesn't support margin trading for {self.active_bot.pair}.",
                    self.active_bot,
                )

            self.controller.update_logs(
                f"Opening new margin deal for {self.active_bot.pair}...",
                self.active_bot,
            )
            self.margin_short_base_order()

        # Update bot no activation required
        if (
            self.active_bot.status == Status.active
            or self.active_bot.deal.opening_price > 0
        ):
            self.active_bot = self.short_update_deal_trailling_parameters()
        else:
            # Activation required
            self.active_bot = self.short_open_deal_trailling_parameters()

        self.controller.save(self.active_bot)
        return self.active_bot
