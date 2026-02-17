from time import sleep, time
from typing import Type, Union

from pybinbot import (
    BotBase,
    round_numbers,
    round_timestamp,
    DealType,
    Status,
    OrderSide,
    OrderStatus,
    OrderType,
    Strategy,
)
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from bots.models import BotModel, OrderModel
from exchange_apis.kucoin.futures.futures_deal import KucoinFuturesDeal
from kucoin_universal_sdk.generate.futures.order.model_add_order_req import (
    AddOrderReq,
)


class FuturesLongDeal(KucoinFuturesDeal):
    """
    Long deal implementation for Kucoin futures trading.

    Happens after open_deal is executed
    formerly known as streaming updates
    these operations are triggered by websockets
    """

    def __init__(
        self, bot: BotModel, db_table: Type[Union[BotTable, PaperTradingTable]]
    ) -> None:
        super().__init__(bot=bot, db_table=db_table)
        self.active_bot = bot

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
                self.controller.update_logs(
                    bot=self.active_bot,
                    log_message="No open futures position to take profit on.",
                )
                return self.active_bot

            qty = round_numbers(abs(float(position.current_qty)), 8)
            if self.active_bot.strategy == Strategy.margin_short:
                self.controller.update_logs(
                    "Dispatching futures buy order for take profit...",
                    self.active_bot,
                )
                order = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    reduce_only=True,
                )
            else:
                self.controller.update_logs(
                    "Dispatching futures sell order for take profit...",
                    self.active_bot,
                )
                order = self.kucoin_futures_api.place_futures_order(
                    symbol=self.kucoin_symbol,
                    side=AddOrderReq.SideEnum.SELL,
                    size=qty,
                    order_type=OrderType.market,
                    reduce_only=True,
                )

            # We don't have full fee info here; focus on core fields
            price = float(order.price) if getattr(order, "price", None) else 0.0
            order_data = OrderModel(
                timestamp=int(time() * 1000),
                order_id=order.order_id,
                deal_type=DealType.take_profit,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type="MARKET",
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = float(order_data.price)
        self.active_bot.deal.closing_qty = float(order_data.qty)
        self.active_bot.deal.closing_timestamp = round_timestamp(order_data.timestamp)
        self.active_bot.status = Status.completed

        bot = self.controller.save(self.active_bot)
        bot = BotModel.model_construct(**bot.model_dump())
        self.controller.update_logs(
            bot=self.active_bot, log_message="Completed futures take profit."
        )

        return bot

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
            position = self.kucoin_futures_api.get_futures_position(self.kucoin_symbol)
            if not position or float(position.current_qty) == 0:
                self.controller.update_logs(
                    bot=self.active_bot,
                    log_message="No open futures position to stop out.",
                )
                return self.active_bot

            qty = round_numbers(abs(float(position.current_qty)), 8)
            if self.active_bot.strategy == Strategy.margin_short:
                order = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    reduce_only=True,
                )
            else:
                order = self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    reduce_only=True,
                )

            price = float(order.price) if getattr(order, "price", None) else 0.0
            close_side = (
                OrderSide.buy
                if self.active_bot.strategy == Strategy.margin_short
                else OrderSide.sell
            )
            stop_loss_order = OrderModel(
                timestamp=int(time() * 1000),
                order_id=order.order_id,
                deal_type=DealType.stop_loss,
                pair=self.kucoin_symbol,
                order_side=close_side,
                order_type=OrderType.limit,
                price=price,
                qty=float(qty),
                time_in_force="GTC",
                status=OrderStatus.FILLED,
            )

        self.active_bot.orders.append(stop_loss_order)
        self.active_bot.deal.closing_price = float(stop_loss_order.price)
        self.active_bot.deal.closing_qty = float(stop_loss_order.qty)
        self.active_bot.deal.closing_timestamp = stop_loss_order.timestamp
        self.active_bot.add_log("Completed futures Stop loss.")

        self.active_bot.status = Status.completed
        self.controller.save(self.active_bot)

        return self.active_bot

    def trailling_profit(self, repurchase_multiplier: float = 1) -> BotModel | None:
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
                self.controller.update_logs(
                    "qty=0, unable to execute futures trailling_profit",
                    self.active_bot,
                )
                self.active_bot.status = Status.error
                self.controller.save(self.active_bot)
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
            if self.active_bot.strategy == Strategy.margin_short:
                order = self.kucoin_futures_api.buy(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    reduce_only=True,
                )
            else:
                order = self.kucoin_futures_api.sell(
                    symbol=self.kucoin_symbol,
                    qty=qty,
                    reduce_only=True,
                )

            price = float(order.price)
            order.deal_type = DealType.trailling_profit
            order_data = order

        self.active_bot.orders.append(order_data)

        self.active_bot.deal.trailling_profit_price = float(order_data.price)
        deviation_pct = float(self.active_bot.trailling_deviation or 0) / 100
        if self.active_bot.strategy == Strategy.margin_short:
            trailling_stop_loss_price = float(order_data.price) + (
                float(order_data.price) * deviation_pct
            )
        else:
            trailling_stop_loss_price = float(order_data.price) - (
                float(order_data.price) * deviation_pct
            )
        self.active_bot.deal.trailling_stop_loss_price = round_numbers(
            trailling_stop_loss_price, self.price_precision
        )

        # new deal parameters to replace previous
        self.active_bot.deal.closing_price = float(order_data.price)
        self.active_bot.deal.closing_qty = float(order_data.qty)
        self.active_bot.deal.closing_timestamp = round_timestamp(order_data.timestamp)

        self.active_bot.status = Status.completed
        self.active_bot.add_log(
            "Completed futures take profit after failing to break trailling"
        )
        self.controller.save(self.active_bot)

        return self.active_bot

    def reverse_to_short(self) -> BotModel:
        """
        After hitting stop loss, open a short position with a new bot/deal.
            - Create a new bot with the same parameters but strategy.short and status.inactive
            - Activate the new bot (open a short deal)
            - Update logs for both bots
            - Save changes to the database
            - Return the updated short bot model
            - Note: This method assumes that the current active bot is a long position that just got stopped out.
            - It also assumes that margin_short_reversal is enabled, which allows automatic reversal from long to short after stop loss.
        """
        # Step 2: Construct new short bot
        new_bot_data = self.active_bot.model_dump()
        new_bot = BotBase.model_construct(**new_bot_data)
        new_bot.strategy = Strategy.margin_short
        new_bot.status = Status.inactive
        new_bot.logs = []
        bot = self.bot_crud.create(new_bot)

        # Activate
        bot = self.bot_crud.get_one(bot_id=str(bot.id))
        self.active_bot = BotModel.model_construct(**bot.model_dump())
        self.open_deal()

        self.controller.save(self.active_bot)
        self.controller.update_logs(
            "Reversed long into short successfully.", self.active_bot
        )
        return self.active_bot

    def exit_long(self, close_price: float, open_price: float) -> BotModel:
        """
        Exist logic when strategy.long
        """
        current_price = round_numbers(close_price, self.price_precision)
        self.active_bot.deal.current_price = current_price
        self.controller.save(self.active_bot)

        # Stop loss
        if (
            self.active_bot.stop_loss > 0
            # current_price below stop loss
            and self.active_bot.deal.stop_loss_price > current_price
        ):
            self.execute_stop_loss()
            # Makes sure that order completes
            sleep(5)
            if self.active_bot.margin_short_reversal:
                # If margin short reversal is enabled, we want to open a short position after stop loss is hit
                self.controller.update_logs(
                    "Margin short reversal enabled, opening short position after stop loss...",
                    self.active_bot,
                )
                self.active_bot = self.reverse_to_short()

        # Trailling profit
        if self.active_bot.trailling and self.active_bot.deal.opening_price > 0:
            # If current price didn't break take_profit_trail (first time hitting take_profit or trailling_deviation lower than base_order buy_price so trailling stop loss is not set at this point)
            if self.active_bot.deal.trailling_stop_loss_price == 0:
                trailling_price = float(self.active_bot.deal.opening_price) * (
                    1 + (float(self.active_bot.trailling_profit) / 100)
                )
            else:
                # new trail price = current trailling stop loss + trail profit
                trailling_price = float(
                    self.active_bot.deal.trailling_stop_loss_price
                ) * (1 + (self.active_bot.trailling_profit / 100))

            self.active_bot.deal.trailling_profit_price = round_numbers(
                trailling_price, self.price_precision
            )
            # Direction 1 (upward): breaking the current trailling
            if current_price >= trailling_price:
                new_take_profit = current_price * (
                    1 + ((self.active_bot.trailling_profit) / 100)
                )
                new_trailling_stop_loss: float = current_price - (
                    current_price * ((self.active_bot.trailling_deviation) / 100)
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
                    self.active_bot.deal.trailling_stop_loss_price = round_numbers(
                        new_trailling_stop_loss, self.price_precision
                    )

                if (
                    old_trailling_stop_loss
                    != self.active_bot.deal.trailling_stop_loss_price
                ):
                    self.active_bot.add_log(
                        f"Updated trailling_stop_loss_price to {self.active_bot.deal.trailling_stop_loss_price}"
                    )

                if (
                    old_trailling_profit_price
                    != self.active_bot.deal.trailling_profit_price
                ):
                    self.active_bot.add_log(
                        f"Updated trailling_profit_price to {round_numbers(self.active_bot.deal.trailling_profit_price, self.price_precision)}"
                    )

                self.controller.save(self.active_bot)

            # Direction 2 (downward): breaking the trailling_stop_loss
            # Make sure it's red candlestick, to avoid slippage loss
            # Sell after hitting trailling stop_loss and if price already broken trailling
            if (
                self.active_bot.deal.trailling_stop_loss_price > 0
                # Broken stop_loss
                and current_price < self.active_bot.deal.trailling_stop_loss_price
                # Red candlestick
                and open_price > current_price
            ):
                self.controller.update_logs(
                    f"Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Selling {self.kucoin_symbol}",
                    self.active_bot,
                )
                self.trailling_profit()

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
        current_price = round_numbers(close_price, self.price_precision)
        self.active_bot.deal.current_price = current_price
        self.controller.save(self.active_bot)

        if self.active_bot.deal.stop_loss_price == 0:
            self.active_bot.deal.stop_loss_price = (
                self.active_bot.deal.opening_price
                + (
                    self.active_bot.deal.opening_price
                    * (self.active_bot.stop_loss / 100)
                )
            )

        if (
            self.active_bot.stop_loss > 0
            and current_price > self.active_bot.deal.stop_loss_price
        ):
            self.controller.update_logs(
                f"Executing futures short stop_loss after hitting {self.active_bot.deal.stop_loss_price}",
                self.active_bot,
            )
            self.execute_stop_loss()
            self.controller.save(self.active_bot)
            return self.active_bot

        if (
            current_price > 0
            and self.active_bot.trailling
            and self.active_bot.trailling_profit > 0
            and self.active_bot.trailling_deviation > 0
        ):
            if (
                self.active_bot.deal.trailling_profit_price == 0
                or current_price < self.active_bot.deal.trailling_profit_price
            ):
                self.update_short_trailing(current_price)

            if (
                self.active_bot.deal.trailling_stop_loss_price > 0
                and current_price > self.active_bot.deal.trailling_stop_loss_price
            ):
                self.controller.update_logs(
                    f"Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Buying {self.kucoin_symbol}",
                    self.active_bot,
                )
                self.trailling_profit()
                return self.active_bot

        if (
            not self.active_bot.trailling
            and self.active_bot.deal.take_profit_price
            and current_price <= self.active_bot.deal.take_profit_price
        ):
            self.controller.update_logs(
                f"Executing futures short take_profit after hitting {self.active_bot.deal.take_profit_price}",
                self.active_bot,
            )
            self.take_profit_order()

        return self.active_bot

    def update_short_trailing(self, close_price: float) -> None:
        deal = self.active_bot.deal
        opening_price = float(deal.opening_price)
        if opening_price <= 0:
            return

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

    def deal_exit_orchestration(self, close_price: float, open_price: float):
        if self.active_bot.strategy == Strategy.margin_short:
            return self.exit_short(close_price)
        return self.exit_long(close_price, open_price)
