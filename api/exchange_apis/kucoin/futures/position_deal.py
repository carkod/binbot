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

    def _is_reversal_possible(
        self, mark_price, current_contracts, flip_contracts
    ) -> tuple[bool, str]:
        multiplier = float(
            self.kucoin_symbol_data.multiplier
            or self.kucoin_futures_api.DEFAULT_MULTIPLIER
        )
        taker_fee_rate = float(self.kucoin_symbol_data.taker_fee_rate or 0)
        maintenance_margin = float(self.kucoin_symbol_data.maintain_margin or 0)
        available_balance = float(self.compute_available_balance())
        leverage = float(self.kucoin_futures_api.DEFAULT_LEVERAGE)

        current_notional = current_contracts * mark_price * multiplier
        flip_notional = flip_contracts * mark_price * multiplier
        reusable_initial_margin = current_notional / leverage
        estimated_flip_fees = flip_notional * taker_fee_rate
        estimated_required_buffer = (
            current_notional / leverage + maintenance_margin + estimated_flip_fees
        )
        estimated_available_buffer = available_balance + reusable_initial_margin

        msg = (
            "Pre-check failed: insufficient estimated margin for reversal. "
            f"Current position: {current_contracts} contracts, flip order: {flip_contracts} contracts, "
            f"available balance: {round_numbers(available_balance, 4)}, "
            f"reusable margin estimate: {round_numbers(reusable_initial_margin, 4)}, "
            f"required buffer estimate: {round_numbers(estimated_required_buffer, 4)}."
        )

        can_reverse = estimated_available_buffer >= estimated_required_buffer
        return can_reverse, msg

    def estimate_reversal_possible_for_new_bot(self) -> tuple[bool, str]:
        """
        Estimate whether a newly activated futures bot is likely to support a
        same-size one-order reversal later.

        This is weaker than the live reversal pre-check because there is no
        current exchange position yet; it estimates contracts from the current
        market and then reuses the internal affordability logic.
        """
        if not self.active_bot.margin_short_reversal or self.active_bot.stop_loss <= 0:
            return True, ""

        side = (
            AddOrderReq.SideEnum.SELL
            if self.active_bot.strategy == Strategy.margin_short
            else AddOrderReq.SideEnum.BUY
        )
        estimated_price = self.kucoin_futures_api.matching_engine(
            symbol=self.kucoin_symbol,
            side=side,
            size=1,
        )
        estimated_contracts = self.calculate_contracts(estimated_price)

        if estimated_contracts <= 0:
            return (
                False,
                "Pre-check estimate failed: bot could not estimate a valid futures position size for reversal support.",
            )

        flip_contracts = round_numbers(estimated_contracts * 2, self.qty_precision)
        can_reverse, msg = self._is_reversal_possible(
            estimated_price, estimated_contracts, flip_contracts
        )
        if can_reverse:
            return True, ""

        msg = msg.replace("Pre-check failed", "Pre-check estimate failed", 1)
        msg = (
            f"{msg} Estimated entry price: {round_numbers(estimated_price, self.price_precision)}, "
            f"estimated position: {estimated_contracts} contracts, estimated flip order: {flip_contracts} contracts."
        )
        return False, msg

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
                return self.active_bot

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
                else:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message=f"Failed to execute stop loss order: {str(e.response.message)}",
                    )
                    self.active_bot.status = Status.error
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
        Place the closing position (stop loss in Kucoin) when the bot (long or short) is
        in a profitable position

        This only places the stop loss order at the exchange, the actual bot status and deal parameters will be updated when the order is filled and the system receives the update via websocket (handled in futures_position.order_updates)
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

        self.remove_stale_orders()
        self.active_bot.orders.append(order_data)

        if order_data.status != OrderStatus.FILLED:
            self.active_bot.add_log(
                f"Trailing profit order not filled immediately, got status {order_data.status}"
            )
        else:
            self.active_bot.add_log(
                "Completed futures take profit after failing to break trailing"
            )

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
        source_bot = self.active_bot

        # Strategy toggle
        target_strategy = (
            Strategy.margin_short
            if source_bot.strategy == Strategy.long
            else Strategy.long
        )

        # Pre-close current bot
        previous_bot = deepcopy(source_bot)
        previous_bot.add_log(
            f"Skipped stop loss and reversing to {target_strategy.value} in a new bot."
        )
        self.controller.save(previous_bot)

        current_position = self.kucoin_futures_api.get_futures_position(
            self.kucoin_symbol
        )
        current_contracts = (
            round_numbers(abs(float(current_position.current_qty)), self.qty_precision)
            if current_position and float(current_position.current_qty) != 0
            else 0
        )

        if current_contracts <= 0:
            msg = "No open futures position found to reverse, skipping reversal."
            previous_bot.add_log(msg)
            self.controller.save(previous_bot)
            source_bot.add_log(msg)
            source_bot.status = Status.error
            self.controller.save(source_bot)
            self.active_bot = source_bot
            return source_bot

        # One KuCoin futures order can flip the net position.
        # To preserve size, submit the current position size twice:
        # one leg closes the existing side, the second leg becomes the new side.
        flip_contracts = round_numbers(current_contracts * 2, self.qty_precision)

        can_reverse, msg = self._is_reversal_possible(
            current_position.mark_price, current_contracts, flip_contracts
        )

        if not can_reverse:
            previous_bot.add_log(msg)
            self.controller.save(previous_bot)
            source_bot.add_log(msg)
            source_bot.status = Status.error
            self.controller.save(source_bot)
            self.active_bot = source_bot
            return source_bot

        # Construct new bot
        new_bot = BotBase(
            pair=source_bot.pair,
            fiat=source_bot.fiat,
            fiat_order_size=source_bot.fiat_order_size,
            quote_asset=source_bot.quote_asset,
            candlestick_interval=source_bot.candlestick_interval,
            market_type=source_bot.market_type,
            close_condition=source_bot.close_condition,
            cooldown=source_bot.cooldown,
            dynamic_trailling=source_bot.dynamic_trailling,
            margin_short_reversal=False,
            name=source_bot.name,
            strategy=target_strategy,
            mode=source_bot.mode,
            status=Status.inactive,
            stop_loss=source_bot.stop_loss,
            take_profit=source_bot.take_profit,
            trailling=source_bot.trailling,
            trailling_deviation=source_bot.trailling_deviation,
            trailling_profit=source_bot.trailling_profit,
            logs=[],
        )
        created_bot = self.controller.create(new_bot)
        reversed_bot = BotModel(**created_bot.model_dump())

        try:
            if reversed_bot.strategy == Strategy.margin_short:
                order = self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=flip_contracts,
                    reduce_only=False,
                )
            else:
                order = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=flip_contracts,
                    reduce_only=False,
                )
            # If successful, allow system to process order
            sleep(10)
        except RestError as kucoin_error:
            msg = kucoin_error.response.message
            reversed_bot.add_log(
                f"Failed to open {target_strategy.value} position during reversal: {msg}"
            )
            reversed_bot.status = Status.error
            self.controller.save(reversed_bot)
            self.active_bot = reversed_bot
            return reversed_bot

        order_model = OrderModel(**order.model_dump())

        # full close previous bot
        # we do this first to avoid half-closed bot if anything fails before
        # in which case we keep previous_bot active
        closing_order = deepcopy(order_model)
        closing_order.deal_type = DealType.margin_short
        previous_bot.orders.append(closing_order)
        previous_bot.deal.closing_price = closing_order.price
        previous_bot.deal.closing_qty = current_contracts
        previous_bot.deal.closing_timestamp = closing_order.timestamp
        previous_bot.add_log("Updated closing deal")
        previous_bot.status = Status.completed
        self.controller.save(previous_bot)

        # Continue new bot logic
        reversed_bot.orders.append(order_model)

        # Allow system to process, sometimes position can be empty immediately
        # after order execution
        position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
        self.active_bot = reversed_bot
        if not position or float(position.current_qty) == 0:
            self.active_bot = self.backfill_position_from_fills()
            return self.active_bot
        new_position_contracts = round_numbers(
            abs(float(position.current_qty)), self.qty_precision
        )

        reversed_bot.deal.base_order_size = new_position_contracts
        reversed_bot.deal.opening_price = order_model.price
        reversed_bot.deal.opening_qty = new_position_contracts
        reversed_bot.deal.opening_timestamp = order_model.timestamp
        reversed_bot.deal.current_price = position.mark_price if position else 0
        reversed_bot.status = (
            Status.active if new_position_contracts > 0 else Status.error
        )
        reversed_bot.add_log(
            f"Futures bot opened @ {reversed_bot.deal.current_price} with {new_position_contracts} contracts"
        )
        self.controller.save(reversed_bot)
        self.active_bot = reversed_bot
        if reversed_bot.status == Status.active:
            self.update_parameters()
        # testing. make sure trailing_stop loss has been reset after reversal
        return reversed_bot

    def exit(self, close_price: float, _: float | None = None) -> BotModel:
        """
        Exit logic for futures positions.
        """
        current_price = round_numbers(close_price, self.price_precision)
        self.active_bot.deal.current_price = current_price
        self.controller.save(self.active_bot)

        direction = self._direction_multiplier()
        position_name = self.active_bot.strategy.value

        # panic close low activity assets
        opening_price = float(self.active_bot.deal.opening_price)
        bot_profit = (
            ((current_price - opening_price) / opening_price) * 100 * direction
            if opening_price > 0
            else 0
        )
        is_3_days = (
            self.active_bot.deal.opening_timestamp
            and (int(time() * 1000) - self.active_bot.deal.opening_timestamp)
            >= 3 * 24 * 60 * 60 * 1000
        )
        # Panic close only low-profit positions after 3 days.
        if 0 < bot_profit < 1 and is_3_days:
            self.controller.update_logs(
                f"Panic close triggered for {position_name} due to {'3 days elapsed' if is_3_days else 'unprofitable position'} with profit {bot_profit}. Closing position immediately.",
                self.active_bot,
            )
            self.close_all()
            return self.active_bot

        if self.active_bot.deal.stop_loss_price == 0:
            entry_price = float(self.active_bot.deal.opening_price)
            delta = entry_price * (self.active_bot.stop_loss / 100)
            self.active_bot.deal.stop_loss_price = round_numbers(
                entry_price - (delta * direction),
                self.price_precision,
            )

        if (
            self.active_bot.stop_loss > 0
            and ((current_price - self.active_bot.deal.stop_loss_price) * direction) < 0
        ):
            if self.active_bot.margin_short_reversal:
                self.controller.update_logs(
                    f"Margin short reversal enabled, opening {self.active_bot.strategy.value} position after stop loss...",
                    self.active_bot,
                )
                self.active_bot = self.reverse_position()
            else:
                self.controller.update_logs(
                    f"Executing futures {position_name} stop_loss after hitting {self.active_bot.deal.stop_loss_price}",
                    self.active_bot,
                )
                self.execute_stop_loss()

        # Trailling profit (price going down)
        if self.active_bot.trailling and self.active_bot.deal.opening_price > 0:
            # First activation: derive the next trailing trigger from entry or the last trailing stop.
            if self.active_bot.deal.trailling_stop_loss_price == 0:
                trailing_price = float(self.active_bot.deal.opening_price) * (
                    1 + direction * (float(self.active_bot.trailling_profit) / 100)
                )
                trailing_price = round_numbers(trailing_price, self.price_precision)
            else:
                # Advance the trailing trigger in the profitable direction.
                trailing_price = float(
                    self.active_bot.deal.trailling_stop_loss_price
                ) * (1 + direction * (self.active_bot.trailling_profit / 100))
                trailing_price = round_numbers(trailing_price, self.price_precision)

            self.active_bot.deal.trailling_profit_price = round_numbers(
                trailing_price, self.price_precision
            )
            if (current_price - trailing_price) * direction >= 0:
                new_take_profit = current_price * (
                    1 + direction * ((self.active_bot.trailling_profit) / 100)
                )
                new_trailling_stop_loss: float = round_numbers(
                    current_price
                    - direction
                    * (current_price * ((self.active_bot.trailling_deviation) / 100)),
                    self.price_precision,
                )

                # Avoid duplicate logs
                old_trailling_profit_price = self.active_bot.deal.trailling_profit_price
                old_trailling_stop_loss = self.active_bot.deal.trailling_stop_loss_price

                # Keep the next trailing trigger ahead of the current price move.
                self.active_bot.deal.trailling_profit_price = round_numbers(
                    new_take_profit, self.price_precision
                )

                if (
                    new_trailling_stop_loss - self.active_bot.deal.opening_price
                ) * direction > 0 and (
                    self.active_bot.deal.trailling_stop_loss_price == 0
                    or (
                        new_trailling_stop_loss
                        - self.active_bot.deal.trailling_stop_loss_price
                    )
                    * direction
                    > 0
                ):
                    # Only move the trailing stop deeper into profit.
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
            if (
                current_price - self.active_bot.deal.take_profit_price
            ) * direction >= 0:
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

        self.active_bot = cls.order_updates()
        cls.active_bot = self.active_bot
        self.active_bot = cls.position_updates()
        cls.active_bot = self.active_bot

        open_price = float(self.klines[-1][1])
        if not close_price or close_price == 0:
            close_price = self.klines[-1][4]

        self.active_bot.deal.current_price = close_price
        self.controller.save(self.active_bot)

        if self.active_bot.dynamic_trailling:
            cls.market_trailing_analytics(current_price=close_price)

        try:
            return self.exit(close_price, open_price)
        except RestError as kucoin_error:
            msg = kucoin_error.response.message
            self.controller.update_logs(
                f"Error during deal exit orchestration. Message: {msg}", self.active_bot
            )
            return self.active_bot
