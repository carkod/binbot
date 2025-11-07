from time import sleep
from typing import Type, Union
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.symbols_crud import SymbolsCrud
from bots.models import BotModel, OrderModel
from tools.enum_definitions import DealType, OrderSide, Status, QuoteAssets, Strategy
from tools.exceptions import BinanceErrors, TakeProfitError
from tools.maths import (
    round_numbers,
    round_timestamp,
    round_numbers_floor,
    round_numbers_ceiling,
)
from deals.abstractions.base import BaseDeal
from databases.crud.paper_trading_crud import PaperTradingTableCrud


class DealAbstract(BaseDeal):
    MIN_EXCHANGE_AMOUNT = 15
    """
    Centralized deal controller.

    This is the first step that comes after a bot is saved
    1. Save bot
    2. Open deal (deal controller)
    3. Update deals (deal update controller)

    - db_collection = ["bots", "paper_trading"].
    paper_trading uses simulated orders and bot uses real binance orders.
    PaperTradingTable is implemented, PaperTradingController with the db operations is not.
    - bot: BotModel (at some point to refactor into BotTable as they are both pydantic models)
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
        self.symbol_info = self.symbols_crud.get_symbol(self.active_bot.pair)
        self.conversion_threshold = 1.05

    def handle_existing_quote_balance(self, symbol: str, is_quote_balance: float):
        """Handle case when we have existing quote balance"""
        quote_balance = round_numbers_floor(is_quote_balance, self.quote_qty_precision)
        quote_fiat_price = self.get_book_order_deep(
            symbol, not self.active_bot.quote_asset.is_fiat()
        )
        total_qty_available = quote_fiat_price * quote_balance

        if self.active_bot.quote_asset.is_fiat():
            return quote_balance / quote_fiat_price

        # Check if we have enough balance (with conversion threshold buffer)
        required_amount = self.active_bot.fiat_order_size * self.conversion_threshold
        if total_qty_available > required_amount:
            return None

        # Calculate amount missing and buy the difference
        amount_missing = self.active_bot.fiat_order_size - total_qty_available
        return self.buy_missing_amount(symbol, amount_missing, quote_fiat_price)

    def handle_no_quote_balance(self, symbol: str):
        """
        Handle case when we have no quote balance
        """
        quote_fiat_price = self.get_book_order_deep(symbol, True)
        quote_asset_qty = round_numbers_floor(
            self.active_bot.fiat_order_size / quote_fiat_price,
            self.quote_qty_precision,
        )
        total_qty_available_buy = round_numbers_floor(
            quote_fiat_price * quote_asset_qty,
            self.quote_qty_precision,
        )

        # Check if calculated amount exceeds required amount
        if total_qty_available_buy > self.active_bot.fiat_order_size:
            return None

        # Buy the calculated amount with conversion threshold
        return self.buy_order(
            symbol=symbol,
            qty=quote_asset_qty * self.conversion_threshold,
            qty_precision=self.quote_qty_precision,
        )

    def buy_missing_amount(
        self, symbol: str, amount_missing: float, quote_fiat_price: float
    ):
        if amount_missing < self.MIN_EXCHANGE_AMOUNT:
            # Use minimum exchange amount
            qty = round_numbers_ceiling(self.MIN_EXCHANGE_AMOUNT / quote_fiat_price)
        else:
            # Buy the exact amount needed
            qty = round_numbers_ceiling(amount_missing / float(quote_fiat_price))

        return self.buy_order(
            symbol=symbol,
            qty=qty * self.conversion_threshold,
            qty_precision=self.quote_qty_precision,
        )

    def calculate_avg_price(self, fills: list[dict]) -> float:
        """
        Calculate average price of fills
        """
        total_qty: float = 0
        total_price: float = 0
        for fill in fills:
            total_qty += float(fill["qty"])
            total_price += float(fill["price"]) * float(fill["qty"])
        return total_price / total_qty

    def check_available_balance_fiat(self, balances: list[dict]):
        """
        Handle fiat quote asset balance checking and conversion.
        This is for when the quote asset itself is a fiat currency (e.g., TRY, EUR).
        """
        symbol = self.active_bot.fiat + self.active_bot.quote_asset.value

        if isinstance(self.controller, PaperTradingTableCrud):
            return self.simulate_order(symbol, OrderSide.buy)

        price = self.get_book_order_deep(symbol, False)

        # Get current quote asset balance
        conversion_qty = next(
            (
                float(b["free"])
                for b in balances
                if b["asset"] == self.active_bot.quote_asset.value
            ),
            None,
        )

        if not conversion_qty:
            return self.handle_fiat_conversion_sell(
                symbol=symbol, amount_missing=self.active_bot.fiat_order_size
            )

        total_available = conversion_qty / price if conversion_qty else 0
        amount_missing = self.active_bot.fiat_order_size - total_available

        # Only proceed if we have quote asset but total available is 0 or insufficient
        if conversion_qty and (total_available == 0 or amount_missing > 0):
            return self.handle_fiat_conversion_sell(symbol, amount_missing)

        return None

    def handle_fiat_conversion_sell(self, symbol: str, amount_missing: float):
        """Handle selling fiat quote asset to get base fiat currency"""
        precision = self.calculate_qty_precision(symbol)

        # Determine quantity to sell
        qty = (
            self.MIN_EXCHANGE_AMOUNT
            if amount_missing <= self.MIN_EXCHANGE_AMOUNT
            else amount_missing
        )

        # Apply conversion threshold and round up
        qty = round_numbers_ceiling(qty * self.conversion_threshold, precision)

        return self.sell_order(
            symbol=symbol,
            qty=qty,
            qty_precision=precision,
        )

    def check_available_balance(self):
        """
        Check if the base asset is supported

        For quote asset transactions we always want to round down (floor)
        to avoid insufficient balance errors

        1. Do we have quote asset?
            1.1 we do have quote asset but not enough - buy the difference
            1.2 we do have quote asset and we do have enough - don't do anything

        2. we don't have quote asset, buy the full fiat amount
            2.1. convert available fiat to quote
            2.2. buy base asset
        """
        balances = self.get_raw_balance()
        symbol = self.active_bot.quote_asset.value + self.active_bot.fiat

        if self.active_bot.quote_asset.is_fiat():
            return self.check_available_balance_fiat(balances)

        # we don't need to continue if it's a fake bot
        if isinstance(self.controller, PaperTradingTableCrud):
            return self.simulate_order(symbol, OrderSide.buy)

        is_quote_balance = next(
            (
                float(b["free"])
                for b in balances
                if b["asset"] == self.active_bot.quote_asset
            ),
            None,
        )
        if is_quote_balance and is_quote_balance > 0:
            quote_balance = round_numbers_floor(
                is_quote_balance, self.quote_qty_precision
            )
            quote_fiat_price = self.get_book_order_deep(
                symbol, not self.active_bot.quote_asset.is_fiat()
            )
            total_qty_available = quote_fiat_price * quote_balance

            # Check if we have enough balance (with conversion threshold buffer)
            required_amount = (
                self.active_bot.fiat_order_size * self.conversion_threshold
            )
            if total_qty_available > required_amount:
                return None

            # Calculate amount missing and buy the difference
            amount_missing = self.active_bot.fiat_order_size - total_qty_available
            if self.active_bot.strategy == Strategy.margin_short:
                qty = (
                    amount_missing / float(quote_fiat_price)
                ) * self.conversion_threshold
            else:
                qty = amount_missing

            return self.buy_missing_amount(symbol, qty, quote_fiat_price)

        else:
            quote_fiat_price = self.get_book_order_deep(symbol, True)
            quote_asset_qty = round_numbers_floor(
                self.active_bot.fiat_order_size / quote_fiat_price,
                self.quote_qty_precision,
            )
            total_qty_available_buy = round_numbers_floor(
                quote_fiat_price * quote_asset_qty,
                self.quote_qty_precision,
            )

            # Check if calculated amount exceeds required amount
            if total_qty_available_buy > self.active_bot.fiat_order_size:
                return None

            # Buy the calculated amount with conversion threshold
            return self.buy_order(
                symbol=symbol,
                qty=quote_asset_qty * self.conversion_threshold,
                qty_precision=self.quote_qty_precision,
            )

    def sell_quote_asset(self) -> BotModel:
        """
        Sell quote asset back to fiat (hedge cyrpto)

        1. Are we using a quote asset that is not fiat?
        2. Do we have quote asset?
            1.1 we do have quote asset sell
            1.2. we don't have quote asset
        """

        if self.active_bot.quote_asset.value == self.active_bot.fiat:
            return self.active_bot

        balances = self.get_raw_balance()

        if self.active_bot.quote_asset.is_fiat():
            # If USDC/TRY buy back not sell
            symbol = self.active_bot.fiat + self.active_bot.quote_asset.value
        else:
            symbol = self.active_bot.quote_asset.value + self.active_bot.fiat

        is_quote_balance = next(
            (
                float(b["free"])
                for b in balances
                if b["asset"] == self.active_bot.quote_asset
            ),
            None,
        )
        if is_quote_balance and is_quote_balance > 0:
            quote_balance = round_numbers_floor(
                is_quote_balance, self.quote_qty_precision
            )

            if self.active_bot.quote_asset.is_fiat():
                # pessimistic price so that we can actually buy more
                quote_fiat_price = self.matching_engine(symbol=symbol, order_side=True)
                # sell everything that is on the account clean
                # this is to hedge from market fluctuations that make affect portfolio value
                total_qty_available = round_numbers_floor(
                    quote_fiat_price * quote_balance
                )
                if total_qty_available < 15:
                    # can't sell such a small amount
                    return self.active_bot

                base_balance = round_numbers_floor(quote_balance / quote_fiat_price)

                if base_balance < 15:
                    self.controller.update_logs(
                        "Can't sell quote asset, it's too small", self.active_bot
                    )
                    return self.active_bot

                # Calculate buy quantity with conversion threshold
                # avoids LOT_SIZE failures
                buy_qty = round_numbers_floor(
                    base_balance,
                    self.quote_qty_precision,
                )

                res = self.buy_order(
                    symbol=symbol,
                    qty=buy_qty,
                    qty_precision=self.quote_qty_precision,
                )
            else:
                quote_fiat_price = self.matching_engine(symbol=symbol, order_side=False)

                total_qty_available = round_numbers_floor(
                    quote_fiat_price * quote_balance
                )
                if total_qty_available < 15:
                    # can't sell such a small amount
                    return self.active_bot

                sell_qty = round_numbers_floor(
                    quote_balance,
                    self.quote_qty_precision,
                )
                res = self.sell_order(
                    symbol=symbol,
                    qty=sell_qty,
                    qty_precision=self.quote_qty_precision,
                )
            if res:
                quote_order = OrderModel(
                    timestamp=int(res["transactTime"]),
                    order_id=int(res["orderId"]),
                    deal_type=DealType.conversion,
                    pair=res["symbol"],
                    order_side=res["side"],
                    order_type=res["type"],
                    price=float(res["price"]),
                    qty=float(res["origQty"]),
                    time_in_force=res["timeInForce"],
                    status=res["status"],
                )
                self.active_bot.orders.append(quote_order)
                self.controller.save(self.active_bot)

        return self.active_bot

    def take_profit_order(self) -> BotModel:
        """
        take profit order (Binance take_profit)
        - We only have stop_price, because there are no book bids/asks in t0
        - take_profit order can ONLY be executed once base order is filled (on Binance)
        """

        deal_buy_price = self.active_bot.deal.opening_price
        buy_total_qty = self.active_bot.deal.opening_qty
        price = (1 + (float(self.active_bot.take_profit) / 100)) * float(deal_buy_price)

        if self.db_table == PaperTradingTable:
            qty = self.active_bot.deal.opening_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)

        qty = round_numbers(buy_total_qty, self.qty_precision)
        price = round_numbers(price, self.price_precision)

        if self.db_table == PaperTradingTable:
            res = self.simulate_order(self.active_bot.pair, OrderSide.sell)
        else:
            qty = round_numbers(qty, self.qty_precision)
            price = round_numbers(price, self.price_precision)
            res = self.sell_order(symbol=self.active_bot.pair, qty=qty)

        # If error pass it up to parent function, can't continue
        if "error" in res:
            raise TakeProfitError(res["error"])

        price = float(res["price"])
        if price == 0:
            # Market orders return 0
            price = self.calculate_avg_price(res["fills"])

        order_data = OrderModel(
            timestamp=int(res["transactTime"]),
            order_id=int(res["orderId"]),
            deal_type=DealType.take_profit,
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=price,
            qty=float(res["origQty"]),
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.deal.total_commissions += self.calculate_total_commissions(
            res["fills"]
        )

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = price
        self.active_bot.deal.closing_qty = float(res["origQty"])
        self.active_bot.deal.closing_timestamp = round_timestamp(res["transactTime"])
        self.active_bot.status = Status.completed

        bot = self.controller.save(self.active_bot)
        bot = BotModel.model_construct(**bot.model_dump())
        self.controller.update_logs(
            bot=self.active_bot, log_message="Completed take profit."
        )

        self.sell_quote_asset()
        return bot

    def base_order(self, repurchase_multiplier: float = 0.95) -> BotModel:
        """
        Required initial order to trigger long strategy bot.
        Other orders require this to execute,
        therefore should fail if not successful

        1. Initial base purchase (0 qty)
            1.1 if not enough quote asset to purchase, redo it with exact qty needed
        2. Set take_profit
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
                if self.active_bot.quote_asset.is_fiat():
                    self.active_bot.deal.base_order_size = float(
                        response["origQty"]
                    ) * float(response["price"])
                # give some time for order to complete
                sleep(3)

            # Long position does not need qty in take_profit
            # initial price with 1 qty should return first match
            last_ticker_price = self.get_book_order_deep(self.active_bot.pair, True)
            price = float(last_ticker_price)

            if self.active_bot.strategy == Strategy.margin_short:
                # Use all available quote asset balance
                # this avoids diffs in ups and downs in prices and fees
                available_quote_asset = self.get_single_raw_balance(
                    self.active_bot.quote_asset
                )
            else:
                available_quote_asset = self.get_single_spot_balance(
                    self.active_bot.quote_asset
                )

            qty = round_numbers_floor(
                (available_quote_asset / float(price)),
                self.qty_precision,
            )

        else:
            self.active_bot.deal.base_order_size = self.active_bot.fiat_order_size
            last_ticker_price = self.last_ticker_price(self.active_bot.pair)
            price = float(last_ticker_price["price"])
            qty = round_numbers_floor(
                (self.active_bot.deal.base_order_size / price),
                self.qty_precision,
            )

        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.simulate_order(
                self.active_bot.pair,
                OrderSide.buy,
            )
        else:
            try:
                res = self.buy_order(
                    symbol=self.active_bot.pair,
                    qty=(qty * repurchase_multiplier),
                )
            except BinanceErrors as error:
                if error.code == -2010:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message=error.message,
                    )
                    if error.message == 'This symbol is not permitted for this account.':
                        return self.active_bot

                    if repurchase_multiplier > 0.80:
                        self.base_order(
                            repurchase_multiplier=repurchase_multiplier - 0.05
                        )
                    return self.active_bot

        self.controller.update_logs(
            bot=self.active_bot, log_message="Base order executed."
        )

        res_price = float(res["price"])

        if self.active_bot.deal.base_order_size == 0:
            self.active_bot.deal.base_order_size = float(res["origQty"]) * res_price

        if res_price == 0:
            # Market orders return 0
            res_price = self.calculate_avg_price(res["fills"])

        order_data = OrderModel(
            timestamp=int(res["transactTime"]),
            order_id=res["orderId"],
            deal_type=DealType.base_order,
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=price,
            qty=float(res["origQty"]),
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.total_commissions += self.calculate_total_commissions(
            res["fills"]
        )

        self.active_bot.deal.opening_timestamp = int(res["transactTime"])
        self.active_bot.deal.opening_price = price
        self.active_bot.deal.opening_qty = float(res["origQty"])
        self.active_bot.deal.current_price = float(res["price"])

        # temporary measures to keep deal up to date
        # once bugs are fixed, this can be removed to improve efficiency
        self.active_bot.status = Status.active
        self.controller.save(self.active_bot)

        return self.active_bot
