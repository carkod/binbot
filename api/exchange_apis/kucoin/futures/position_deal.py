from copy import deepcopy
from time import time
from time import sleep
from typing import Union, Type
from pybinbot import (
    BotBase,
    KucoinFutures,
    KucoinApi,
    OrderBase,
    round_numbers,
    round_timestamp,
    DealType,
    Status,
    OrderSide,
    OrderStatus,
    OrderType,
    Strategy,
    convert_to_kucoin_symbol,
    MarketType,
)
from databases.crud.bot_crud import BotTableCrud
from streaming.futures_position import FuturesPosition
from streaming.spot_position import SpotPosition
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from bots.models import BotModel, OrderModel
from exchange_apis.kucoin.futures.futures_deal import KucoinPositionDeal
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import (
    AddOrderReq,
)
from kucoin_universal_sdk.model.common import RestError


class PositionDeal(KucoinPositionDeal):
    """
    Position-based implementation for Kucoin futures trading.

    Previously called FuturesLongDeal, but long or short position logic is all handled within this class
    since Kucoin Futures logic allows easy isolated margin and switching positions.

    Happens after open_deal is executed
    formerly known as streaming updates
    these operations are triggered by websockets
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[BotTable] | Type[PaperTradingTable] = BotTable,
    ) -> None:
        super().__init__(bot=bot, db_table=db_table)
        self.active_bot = bot
        self.price_precision = self.symbol_info.price_precision
        self.qty_precision = self.symbol_info.qty_precision
        self.kucoin_symbol = convert_to_kucoin_symbol(bot)
        # Inherited variables for mypy
        self.api: KucoinApi | KucoinFutures
        self.controller: BotTableCrud | PaperTradingTableCrud

    def _create_controller(self) -> PaperTradingTableCrud | BotTableCrud:
        """
        Separate sessions to avoid locking database
        when continuously saving (self.controller.save)
        """
        if isinstance(self.controller, PaperTradingTableCrud):
            return PaperTradingTableCrud()
        else:
            return BotTableCrud()

    def take_profit_order(self) -> BotModel:
        """
        Futures take profit:
        - Closes the current futures position with a reduce-only order
          (SELL for longs, BUY for shorts).
        """
        deal_buy_price = self.active_bot.deal.opening_price
        buy_total_qty = self.active_bot.deal.opening_qty
        take_profit_pct = float(self.active_bot.take_profit or 0) / 100
        take_profit_multiplier = (
            1 - take_profit_pct
            if self.active_bot.strategy == Strategy.margin_short
            else 1 + take_profit_pct
        )
        self.active_bot.deal.take_profit_price = take_profit_multiplier * float(
            deal_buy_price
        )
        close_side = (
            OrderSide.buy
            if self.active_bot.strategy == Strategy.margin_short
            else OrderSide.sell
        )

        # Paper trading: do not hit the exchange, just simulate an order
        if isinstance(self.controller, PaperTradingTableCrud):
            price = float(self.active_bot.deal.current_price or deal_buy_price)
            qty = round_numbers(buy_total_qty, 8)
            order_data = OrderModel(
                timestamp=int(time() * 1000),
                order_id="paper-futures-tp",
                deal_type=DealType.take_profit,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type="MARKET",
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )
        else:
            # Real futures: close current LONG position via reduce-only SELL
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
            if not position or float(position.current_qty) == 0:
                self.active_bot = self.backfill_position_from_fills()

            qty = round_numbers(abs(float(position.current_qty)), 8)
            if self.active_bot.strategy == Strategy.margin_short:
                self.controller.update_logs(
                    "Dispatching futures buy order for take profit...",
                    self.active_bot,
                )
                order_base = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    reduce_only=True,
                )
            else:
                self.controller.update_logs(
                    "Dispatching futures sell order for take profit...",
                    self.active_bot,
                )
                order_base = self.kucoin_futures_api.place_futures_order(
                    symbol=self.kucoin_symbol,
                    side=AddOrderReq.SideEnum.SELL,
                    size=qty,
                    order_type=OrderType.market,
                    reduce_only=True,
                )

            order_base.deal_type = DealType.take_profit
            # Convert OrderBase to OrderModel using model_dump/model_construct
            order_data = OrderModel.model_construct(**order_base.model_dump())

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = float(order_data.price)
        self.active_bot.deal.closing_qty = float(order_data.qty)
        self.active_bot.deal.closing_timestamp = round_timestamp(order_data.timestamp)
        self.active_bot.status = Status.completed

        self.active_bot.add_log("Completed futures take profit.")
        self.controller.save(self.active_bot)

        return self.active_bot

    def execute_stop_loss(self) -> BotModel:
        """
        Place a stop loss limit order, since we've hit the threshold

        - Hard sell (order status="FILLED" immediately) initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot
        """
        self.controller.update_logs("Placing Futures stop loss...", self.active_bot)

        # Paper trading: simulate without hitting the exchange
        if isinstance(self.controller, PaperTradingTableCrud):
            qty = self.active_bot.deal.opening_qty
            if qty <= 0:
                return self.active_bot

            price = float(self.active_bot.deal.current_price or 0)
            close_side = (
                OrderSide.buy
                if self.active_bot.strategy == Strategy.margin_short
                else OrderSide.sell
            )
            stop_loss_order = OrderModel(
                timestamp=int(time() * 1000),
                order_id="paper-futures-sl",
                deal_type=DealType.stop_loss,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type=OrderType.limit,
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )
        else:
            qty = self.active_bot.deal.opening_qty
            try:
                if self.active_bot.strategy == Strategy.margin_short:
                    order_base = self.kucoin_futures_api.buy(
                        symbol=self.kucoin_symbol,
                        qty=qty,
                        reduce_only=True,
                    )
                else:
                    order_base = self.kucoin_futures_api.sell(
                        symbol=self.kucoin_symbol,
                        qty=qty,
                        reduce_only=True,
                    )

            except RestError as e:
                if float(e.response.code) == 300009:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message=f"{str(e.response.message)}",
                    )
                    self.active_bot.status = Status.completed
                    self.controller.save(self.active_bot)
                    return self.active_bot

        order_base.deal_type = DealType.stop_loss
        stop_loss_order = OrderModel.model_construct(**order_base.model_dump())

        self.active_bot.orders.append(stop_loss_order)
        self.active_bot.deal.closing_price = float(stop_loss_order.price)
        self.active_bot.deal.closing_qty = float(stop_loss_order.qty)
        self.active_bot.deal.closing_timestamp = stop_loss_order.timestamp
        self.active_bot.add_log("Completed futures Stop loss.")

        if stop_loss_order.status != OrderStatus.FILLED:
            self.controller.update_logs(
                bot=self.active_bot,
                log_message=f"Stop loss order not filled immediately, got status {stop_loss_order.status}. Manual intervention may be required.",
            )
        else:
            self.active_bot.status = Status.completed

        self.controller.save(self.active_bot)

        return self.active_bot

    def place_trailing_stop_loss(
        self, repurchase_multiplier: float = 1
    ) -> BotModel | None:
        """
        Close the position at the current take-profit trail level.
        """

        if isinstance(self.controller, PaperTradingTableCrud):
            # all qty simulated
            qty = self.active_bot.deal.opening_qty or 1.0
            price = float(self.active_bot.deal.current_price or 0)
            close_side = (
                OrderSide.buy
                if self.active_bot.strategy == Strategy.margin_short
                else OrderSide.sell
            )
            order_data = OrderModel(
                timestamp=int(time() * 1000),
                order_id="paper-futures-trail",
                deal_type=DealType.trailling_profit,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type="MARKET",
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )
        else:
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
            if not position or float(position.current_qty) == 0:
                # If position doesn't exist, there's no point in trailing anymore
                # so we backfill orders and finish
                self.backfill_position_from_fills()
                return self.active_bot

            qty = round_numbers(
                abs(float(position.current_qty)) * repurchase_multiplier, 8
            )
            action = (
                "buy" if self.active_bot.strategy == Strategy.margin_short else "sell"
            )
            self.controller.update_logs(
                f"Dispatching futures {action} order for trailling profit...",
                self.active_bot,
            )

            # since trailing_profit only runs when trail is broken
            # we can assume stop loss needs to be replaced
            # if it constantly runs, then we need to add conditional logic
            # to avoid cancelling constantly
            self.cancel_current_sl()

            if self.active_bot.strategy == Strategy.margin_short:
                order_base: OrderBase = self.kucoin_futures_api.place_futures_order(
                    side=AddOrderReq.SideEnum.BUY,
                    symbol=self.kucoin_symbol,
                    size=qty,
                    reduce_only=True,
                    order_type=OrderType.market,
                    stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
                    stop=AddOrderReq.StopEnum.UP,
                    stop_price=self.active_bot.deal.trailling_stop_loss_price,
                )
            else:
                order_base = self.kucoin_futures_api.place_futures_order(
                    side=AddOrderReq.SideEnum.SELL,
                    symbol=self.kucoin_symbol,
                    size=qty,
                    reduce_only=True,
                    order_type=OrderType.market,
                    stop_price_type=AddOrderReq.StopPriceTypeEnum.MARK_PRICE,
                    stop=AddOrderReq.StopEnum.DOWN,
                    stop_price=self.active_bot.deal.trailling_stop_loss_price,
                )

            order_base.deal_type = DealType.trailling_profit
            order_data = OrderModel(**order_base.model_dump())

        self.active_bot.orders.append(order_data)

        # new deal parameters to replace previous
        self.active_bot.deal.closing_price = float(order_data.price)
        self.active_bot.deal.closing_qty = float(order_data.qty)
        self.active_bot.deal.closing_timestamp = round_timestamp(order_data.timestamp)

        if order_data.status != OrderStatus.FILLED:
            self.active_bot.add_log(
                f"Trailing profit order not filled immediately, got status {order_data.status}"
            )
        else:
            self.active_bot.add_log(
                "Completed futures take profit after failing to break trailing"
            )
            self.active_bot.status = Status.completed

        self.controller.save(self.active_bot)
        return self.active_bot

    def reverse_position(self) -> BotModel:
        """
        After hitting stop loss, open a new position (long or short) with a new bot/deal.
        Instead of doing open_deal, we do this because we don't want to close current
        Future position

        - store base order
        - Create a new bot with the given strategy and status.inactive
        - Activate the new bot (open a deal)
        - Save changes to the database
        - Return the updated bot model
        """
        # Strategy toggle
        target_strategy = (
            Strategy.margin_short
            if self.active_bot.strategy == Strategy.long
            else Strategy.long
        )

        # Pre-close current bot
        previous_bot = deepcopy(self.active_bot)
        self.active_bot.deal.closing_price = self.active_bot.deal.stop_loss_price
        self.active_bot.deal.closing_qty = self.active_bot.deal.opening_qty
        self.active_bot.deal.closing_timestamp = int(time() * 1000)
        self.active_bot.status = Status.completed
        self.active_bot.add_log(
            f"Skipped stop loss and reversing to {target_strategy.value} in a new bot."
        )
        self.controller.save(self.active_bot)

        # Construct new bot
        new_bot_data = self.active_bot.model_dump(
            exclude={"id", "created_at", "updated_at", "deal", "orders", "logs"}
        )
        new_bot = BotBase.model_construct(**new_bot_data)
        new_bot.strategy = target_strategy
        new_bot.status = Status.inactive
        new_bot.logs = []
        bot = self.controller.create(new_bot)

        # Activate with separate instance to make sure we have latest data
        self.active_bot = BotModel(**bot.model_dump())

        price = self.kucoin_futures_api.matching_engine(
            symbol=self.kucoin_symbol, side=AddOrderReq.SideEnum.BUY, size=1
        )
        contracts = self.calculate_contracts(price)

        if contracts <= 0:
            self.active_bot.add_log(
                f"Failed to reverse to {target_strategy.value} due to zero contracts calculated."
            )
            self.active_bot.status = Status.error
            self.controller.save(self.active_bot)
            return self.active_bot

        try:
            if self.active_bot.strategy == Strategy.margin_short:
                order = self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=contracts,
                    reduce_only=False,
                )
            else:
                order = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=contracts,
                    reduce_only=False,
                )
            # If successful, allow system to process order
            sleep(10)
        except RestError as kucoin_error:
            msg = kucoin_error.response.message
            self.active_bot.add_log(
                f"Failed to open {target_strategy.value} position during reversal: {msg}"
            )
            self.active_bot.status = Status.error
            self.controller.save(self.active_bot)
            return self.active_bot

        order = OrderModel(**order.model_dump())

        # full close previous bot
        # we do this first to avoid half-closed bot if anything fails before
        closing_order = deepcopy(order)
        closing_order.deal_type = DealType.margin_short
        previous_bot.orders.append(closing_order)
        previous_bot.deal.closing_price = closing_order.price
        previous_bot.deal.closing_qty = closing_order.qty
        previous_bot.deal.closing_timestamp = closing_order.timestamp
        previous_bot.status = Status.completed
        previous_bot.add_log("Updated closing deal")
        self.controller.save(previous_bot)

        # Continue new bot logic
        self.active_bot.orders.append(order)

        # Allow system to process, sometimes position can be empty immediately
        # after order execution
        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
        self.active_bot.deal.base_order_size = contracts
        self.active_bot.deal.opening_price = order.price
        self.active_bot.deal.opening_qty = contracts
        self.active_bot.deal.opening_timestamp = order.timestamp
        self.active_bot.deal.current_price = position.mark_price
        self.active_bot.status = Status.active
        self.active_bot.add_log(
            f"Futures bot opened @ {position.mark_price} with {order.qty} contracts"
        )
        # testing, make sure self.active_bot.orders.append(order) does save in the DB
        self.controller.save(self.active_bot)
        self.update_parameters()
        # testing. make sure trailing_stop loss has been reset after reversal
        return self.active_bot

    def exit_long(self, close_price: float, _: float) -> BotModel:
        """
        Exist logic when strategy.long
        """
        current_price = round_numbers(close_price, self.price_precision)
        self.active_bot.deal.current_price = current_price
        self.controller.save(self.active_bot)

        # Stop loss
        if (
            self.active_bot.stop_loss > 0
            and self.active_bot.deal.stop_loss_price > current_price
        ):
            if self.active_bot.margin_short_reversal:
                self.controller.update_logs(
                    "Margin short reversal enabled, opening short position after stop loss...",
                    self.active_bot,
                )
                self.active_bot = self.reverse_position()
            else:
                self.controller.update_logs(
                    f"Executing futures long stop_loss after hitting {self.active_bot.deal.stop_loss_price}",
                    self.active_bot,
                )
                self.execute_stop_loss()

        # Trailling profit
        if self.active_bot.trailling and self.active_bot.deal.opening_price > 0:
            # If current price didn't break take_profit_trail (first time hitting take_profit or trailling_deviation lower than base_order buy_price so trailling stop loss is not set at this point)
            if self.active_bot.deal.trailling_stop_loss_price == 0:
                trailing_price = float(self.active_bot.deal.opening_price) * (
                    1 + (float(self.active_bot.trailling_profit) / 100)
                )
                trailing_price = round_numbers(trailing_price, self.price_precision)
            else:
                # new trail price = current trailling stop loss + trail profit
                trailing_price = float(
                    self.active_bot.deal.trailling_stop_loss_price
                ) * (1 + (self.active_bot.trailling_profit / 100))
                trailing_price = round_numbers(trailing_price, self.price_precision)

            self.active_bot.deal.trailling_profit_price = round_numbers(
                trailing_price, self.price_precision
            )
            # Direction 1 (upward): breaking the current trailling
            if current_price >= trailing_price:
                new_take_profit = current_price * (
                    1 + ((self.active_bot.trailling_profit) / 100)
                )
                new_trailling_stop_loss: float = round_numbers(
                    current_price
                    - (current_price * ((self.active_bot.trailling_deviation) / 100)),
                    self.price_precision,
                )

                # Avoid duplicate logs
                old_trailling_profit_price = self.active_bot.deal.trailling_profit_price
                old_trailling_stop_loss = self.active_bot.deal.trailling_stop_loss_price

                # take_profit but for trailling, to avoid confusion
                # trailling_profit_price always be > trailling_stop_loss_price
                self.active_bot.deal.trailling_profit_price = round_numbers(
                    new_take_profit, self.price_precision
                )

                if (
                    new_trailling_stop_loss > self.active_bot.deal.opening_price
                    and new_trailling_stop_loss
                    > self.active_bot.deal.trailling_stop_loss_price
                ):
                    # Selling below buy_price will cause a loss
                    # instead let it drop until it hits safety order or stop loss
                    # Update trailling_stop_loss
                    self.active_bot.deal.trailling_stop_loss_price = (
                        new_trailling_stop_loss
                    )
                    self.place_trailing_stop_loss()

                if (
                    old_trailling_stop_loss
                    != self.active_bot.deal.trailling_stop_loss_price
                ):
                    self.active_bot.add_log(
                        f"Updated trailling_stop_loss_price to {self.active_bot.deal.trailling_stop_loss_price} and set trailing stop loss (stop loss in Kucoin)"
                    )

                if (
                    old_trailling_profit_price
                    != self.active_bot.deal.trailling_profit_price
                ):
                    self.active_bot.add_log(
                        f"Updated trailling_profit_price to {round_numbers(self.active_bot.deal.trailling_profit_price, self.price_precision)} and set trailing profit (profit in Kucoin)"
                    )

                self.controller.save(self.active_bot)

        if (
            self.active_bot.take_profit > 0
            and self.active_bot.deal.take_profit_price
            and self.active_bot.deal.opening_price > 0
        ):
            # Take profit
            if current_price >= self.active_bot.deal.take_profit_price:
                self.take_profit_order()

        return self.active_bot

    def exit_short(self, close_price: float) -> BotModel:
        """
        Exit logic when strategy.margin_short (short position)
        Mirrors exit_long but with all conditions flipped for short logic.
        """
        current_price = round_numbers(close_price, self.price_precision)
        self.active_bot.deal.current_price = current_price
        self.controller.save(self.active_bot)

        # Stop loss (for short: price below stop loss triggers SL)
        if self.active_bot.deal.stop_loss_price == 0:
            self.active_bot.deal.stop_loss_price = (
                self.active_bot.deal.opening_price
                - (
                    self.active_bot.deal.opening_price
                    * (self.active_bot.stop_loss / 100)
                )
            )

        if (
            self.active_bot.stop_loss > 0
            and current_price < self.active_bot.deal.stop_loss_price
        ):
            if self.active_bot.margin_short_reversal:
                self.controller.update_logs(
                    "Margin short reversal enabled, opening long position after stop loss...",
                    self.active_bot,
                )
                self.active_bot = self.reverse_position()
            else:
                self.controller.update_logs(
                    f"Executing futures short stop_loss after hitting {self.active_bot.deal.stop_loss_price}",
                    self.active_bot,
                )
                self.execute_stop_loss()
            self.controller.save(self.active_bot)
            return self.active_bot

        # Trailling profit (for short: price going down)
        if self.active_bot.trailling and self.active_bot.deal.opening_price > 0:
            # If current price didn't break take_profit_trail (first time hitting take_profit or trailling_deviation higher than base_order sell_price so trailling stop loss is not set at this point)
            if self.active_bot.deal.trailling_stop_loss_price == 0:
                trailing_price = float(self.active_bot.deal.opening_price) * (
                    1 - (float(self.active_bot.trailling_profit) / 100)
                )
                trailing_price = round_numbers(trailing_price, self.price_precision)
            else:
                # new trail price = current trailling stop loss - trail profit
                trailing_price = float(
                    self.active_bot.deal.trailling_stop_loss_price
                ) * (1 - (self.active_bot.trailling_profit / 100))
                trailing_price = round_numbers(trailing_price, self.price_precision)

            self.active_bot.deal.trailling_profit_price = round_numbers(
                trailing_price, self.price_precision
            )
            # Direction 1 (downward): breaking the current trailling
            if current_price <= trailing_price:
                new_take_profit = current_price * (
                    1 - ((self.active_bot.trailling_profit) / 100)
                )
                new_trailling_stop_loss: float = round_numbers(
                    current_price
                    + (current_price * ((self.active_bot.trailling_deviation) / 100)),
                    self.price_precision,
                )

                # Avoid duplicate logs
                old_trailling_profit_price = self.active_bot.deal.trailling_profit_price
                old_trailling_stop_loss = self.active_bot.deal.trailling_stop_loss_price

                # take_profit but for trailling, to avoid confusion
                # trailling_profit_price always be < trailling_stop_loss_price for short
                self.active_bot.deal.trailling_profit_price = round_numbers(
                    new_take_profit, self.price_precision
                )

                if (
                    new_trailling_stop_loss < self.active_bot.deal.opening_price
                    and new_trailling_stop_loss
                    < self.active_bot.deal.trailling_stop_loss_price
                ):
                    # Selling above sell_price will cause a loss
                    # instead let it rise until it hits safety order or stop loss
                    # Update trailling_stop_loss
                    self.active_bot.deal.trailling_stop_loss_price = (
                        new_trailling_stop_loss
                    )
                    self.place_trailing_stop_loss()

                if (
                    old_trailling_stop_loss
                    != self.active_bot.deal.trailling_stop_loss_price
                ):
                    self.active_bot.add_log(
                        f"Updated trailling_stop_loss_price to {self.active_bot.deal.trailling_stop_loss_price} and set trailing stop loss (stop loss in Kucoin)"
                    )

                if (
                    old_trailling_profit_price
                    != self.active_bot.deal.trailling_profit_price
                ):
                    self.active_bot.add_log(
                        f"Updated trailling_profit_price to {round_numbers(self.active_bot.deal.trailling_profit_price, self.price_precision)} and set trailing profit (profit in Kucoin)"
                    )

                self.controller.save(self.active_bot)

        if (
            self.active_bot.take_profit > 0
            and self.active_bot.deal.take_profit_price
            and self.active_bot.deal.opening_price > 0
        ):
            # Take profit (for short: price below take_profit triggers TP)
            if current_price <= self.active_bot.deal.take_profit_price:
                self.take_profit_order()

        return self.active_bot

    def update_short_trailing(self, close_price: float) -> None:
        deal = self.active_bot.deal
        opening_price = float(deal.opening_price)
        if opening_price <= 0:
            return

        if close_price > 0:
            self.close_price = close_price
            self.active_bot.deal.current_price = close_price

        take_profit_pct = float(self.active_bot.take_profit) / 100
        deviation_pct = float(self.active_bot.trailling_deviation) / 100

        if deal.trailling_stop_loss_price == 0:
            price_reference = (
                close_price if close_price < opening_price else opening_price
            )
            trailling_take_profit = price_reference - (
                price_reference * take_profit_pct
            )
            stop_loss_trailing_price = trailling_take_profit - (
                trailling_take_profit * deviation_pct
            )
            if stop_loss_trailing_price < opening_price:
                deal.trailling_profit_price = trailling_take_profit
                deal.trailling_stop_loss_price = stop_loss_trailing_price
                self.active_bot.add_log(
                    f"{self.kucoin_symbol} below opening_price, setting futures short trailling_stop_loss"
                )
                self.controller.save(self.active_bot)

        if (
            deal.trailling_stop_loss_price > 0
            and deal.trailling_profit_price > 0
            and deal.trailling_stop_loss_price < close_price
        ):
            deal.trailling_stop_loss_price = deal.trailling_profit_price * (
                1 + deviation_pct
            )
            deal.stop_loss_price = 0
            self.controller.update_logs(
                f"{self.kucoin_symbol} Updating after broken first trailling_profit (futures short)",
                self.active_bot,
            )

        if deal.trailling_profit_price == 0:
            return

        if close_price <= deal.trailling_profit_price:
            new_take_profit: float = close_price - (close_price * take_profit_pct)
            new_trailling_stop_loss = close_price * (1 + deviation_pct)
            deal.trailling_profit_price = new_take_profit

            if new_trailling_stop_loss < close_price:
                deal.trailling_stop_loss_price = new_trailling_stop_loss

        self.controller.save(self.active_bot)

    def deal_exit_orchestration(
        self, close_price: float, open_price: float
    ) -> BotModel:
        cls: Union[SpotPosition, FuturesPosition]
        if self.active_bot.market_type == MarketType.FUTURES:
            cls = FuturesPosition(
                base_streaming=self.base_streaming,
                bot=self.active_bot,
                price_precision=self.price_precision,
                qty_precision=self.qty_precision,
                db_table=self.db_table,
            )
            cls.base_streaming.kucoin_benchmark_symbol = "ETHBTCUSDTM"
            self.api = self.base_streaming.kucoin_futures_api
            symbol_info = self.base_streaming.kucoin_futures_api.get_symbol_info(
                self.active_bot.pair
            )
            close_price = symbol_info.last_trade_price
        else:
            cls = SpotPosition(
                base_streaming=self.base_streaming,
                bot=self.active_bot,
                price_precision=self.price_precision,
                qty_precision=self.qty_precision,
                db_table=self.db_table,
            )
            cls.base_streaming.kucoin_benchmark_symbol = "BTC-USDT"
            self.api = self.base_streaming.kucoin_api
            close_price = self.base_streaming.kucoin_api.get_ticker_price(
                self.active_bot.pair
            )

        klines, btc_klines = cls.dataframe_ops()
        # returns raw klines
        self.klines = klines
        self.btc_klines = btc_klines

        cls.order_updates()
        cls.position_updates()

        open_price = float(self.klines[-1][1])
        if not close_price or close_price == 0:
            close_price = self.klines[-1][4]

        self.active_bot.deal.current_price = close_price
        self.controller.save(self.active_bot)

        if self.active_bot.dynamic_trailling:
            self.market_trailing_analytics(
                position_market_cls=cls, current_price=close_price
            )

        try:
            if self.active_bot.strategy == Strategy.margin_short:
                return self.exit_short(close_price)
            return self.exit_long(close_price, open_price)
        except RestError as kucoin_error:
            msg = kucoin_error.response.message
            self.controller.update_logs(
                f"Error during deal exit orchestration. Message: {msg}", self.active_bot
            )
            return self.active_bot
