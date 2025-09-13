from time import sleep
from typing import Type, Union
from databases.models.bot_table import BotTable, PaperTradingTable
from databases.crud.symbols_crud import SymbolsCrud
from bots.models import BotModel, OrderModel
from tools.enum_definitions import DealType, OrderSide, Status, QuoteAssets
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
        self.conversion_threshold = 1.05

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
        is_quote_balance = next(
            (
                float(b["free"])
                for b in balances
                if b["asset"] == self.active_bot.quote_asset
            ),
            None,
        )
        if is_quote_balance:
            quote_balance = round_numbers_floor(
                is_quote_balance, self.quote_qty_precision
            )
            # pessimistic price so that we can actually buy more
            quote_fiat_price = self.get_book_order_deep(symbol, True)
            total_qty_available = quote_fiat_price * quote_balance

            # check total balance and a bit more (conversion causes us to lose a bit from market fluctuations and fees)
            if (
                total_qty_available
                > self.active_bot.fiat_order_size * self.conversion_threshold
            ):
                return None
            else:
                amount_missing = self.active_bot.fiat_order_size - total_qty_available
                # Min exchange
                if amount_missing < 15:
                    qty = round_numbers_ceiling(15 / quote_fiat_price)
                    response = self.buy_order(
                        symbol=symbol,
                        qty=qty * self.conversion_threshold,
                        qty_precision=self.quote_qty_precision,
                    )
                    return response
                else:
                    # here we need ceiling to buy as much as we can
                    quote_amount_needed = round_numbers_ceiling(
                        amount_missing / float(quote_fiat_price)
                    )

                    response = self.buy_order(
                        symbol=symbol,
                        qty=quote_amount_needed * self.conversion_threshold,
                        qty_precision=self.quote_qty_precision,
                    )

                return response

        quote_fiat_price = self.get_book_order_deep(symbol, True)
        quote_asset_qty = round_numbers_floor(
            self.active_bot.fiat_order_size / quote_fiat_price,
            self.quote_qty_precision,
        )
        total_qty_available_buy = round_numbers_floor(
            quote_fiat_price * quote_asset_qty,
            self.quote_qty_precision,
        )

        # USDC (current price * estimated qty) > USDC
        if total_qty_available_buy > self.active_bot.fiat_order_size:
            return None
        else:
            # subtract roughly 0.45% to account for fees and price movements
            response = self.buy_order(
                symbol=symbol,
                qty=quote_asset_qty * self.conversion_threshold,
                qty_precision=self.quote_qty_precision,
            )
            if response:
                return response

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

        self.controller.update_logs("Selling quote asset.", self.active_bot)
        balances = self.get_raw_balance()
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
            # pessimistic price so that we can actually buy more
            quote_fiat_price = self.matching_engine(symbol=symbol, order_side=True)
            # sell everything that is on the account clean
            # this is to hedge from market fluctuations that make affect portfolio value
            total_qty_available = round_numbers_floor(quote_fiat_price * quote_balance)
            if total_qty_available < 15:
                # can't sell such a small amount
                return self.active_bot

            res = self.sell_order(
                symbol=symbol,
                qty=is_quote_balance,
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

        self.active_bot.deal.total_commissions = self.calculate_total_commissions(
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
                # give some time for order to complete
                sleep(3)

            # Long position does not need qty in take_profit
            # initial price with 1 qty should return first match
            last_ticker_price = self.get_book_order_deep(self.active_bot.pair, True)
            price = float(last_ticker_price)

            # Use all available quote asset balance
            # this avoids diffs in ups and downs in prices and fees
            available_quote_asset = self.get_single_raw_balance(
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
                        log_message="Base asset purchase failed! Not enough funds.",
                    )
                    if repurchase_multiplier > 0.80:
                        self.base_order(
                            repurchase_multiplier=repurchase_multiplier - 0.05
                        )
                    return self.active_bot

        res_price = float(res["price"])
        self.controller.update_logs(
            bot=self.active_bot, log_message="Base order executed."
        )

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
        # setup stop_loss_price
        stop_loss_price = 0.0
        if float(self.active_bot.stop_loss) > 0:
            stop_loss_price = price - (price * (float(self.active_bot.stop_loss) / 100))
        tp_price = float(res["price"]) * 1 + (float(self.active_bot.take_profit) / 100)

        self.active_bot.deal.opening_timestamp = int(res["transactTime"])
        self.active_bot.deal.opening_price = price
        self.active_bot.deal.opening_qty = float(res["origQty"])
        self.active_bot.deal.current_price = float(res["price"])
        self.active_bot.deal.take_profit_price = round_numbers(
            tp_price, self.price_precision
        )
        self.active_bot.deal.stop_loss_price = round_numbers(
            stop_loss_price, self.price_precision
        )

        # temporary measures to keep deal up to date
        # once bugs are fixed, this can be removed to improve efficiency
        self.active_bot.status = Status.active
        self.controller.save(self.active_bot)

        # Only signal for the whole activation
        self.base_producer.update_required(self.producer, "EXECUTE_SPOT_OPEN_DEAL")
        return self.active_bot
