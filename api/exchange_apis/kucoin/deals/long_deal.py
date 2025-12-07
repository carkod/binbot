from typing import Type, Union
from tools.maths import round_numbers, round_timestamp
from tools.enum_definitions import (
    DealType,
    Status,
    Strategy,
    OrderSide,
)
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from bots.models import BotModel, OrderModel, BotBase
from exchange_apis.kucoin.deals.spot_deal import KucoinSpotDeal
from exchange_apis.kucoin.deals.margin_deal import KucoinMarginDeal


class KucoinLongDeal(KucoinSpotDeal):
    """
    Long deal implementation for Kucoin spot trading.

    Happens after open_deal is executed
    formerly known as streaming updates
    these operations are triggered by websockets
    """

    def __init__(
        self, bot: BotModel, db_table: Type[Union[BotTable, PaperTradingTable]]
    ) -> None:
        super().__init__(bot=bot, db_table=db_table)
        self.active_bot: BotModel = bot

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
            qty = self.kucoin_api.get_single_spot_balance(self.symbol_info.base_asset)

        qty = round_numbers(buy_total_qty, self.qty_precision)
        price = round_numbers(price, self.price_precision)

        if self.db_table == PaperTradingTable:
            order_response, system_order = self.kucoin_api.simulate_order(
                self.active_bot.pair, OrderSide.sell
            )
        else:
            qty = round_numbers(qty, self.qty_precision)
            price = round_numbers(price, self.price_precision)
            order_response, system_order = self.kucoin_api.sell_order(
                symbol=self.active_bot.pair, qty=qty
            )

        price = float(system_order.price)

        order_data = OrderModel(
            timestamp=order_response.order_time,
            order_id=order_response.order_id,
            deal_type=DealType.take_profit,
            pair=system_order.symbol,
            order_side=system_order.side,
            order_type=system_order.type,
            price=price,
            qty=float(order_response.deal_size),
            time_in_force=system_order.time_in_force,
            status=order_response.status,
        )

        self.active_bot.deal.total_commissions = system_order.fee

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = price
        self.active_bot.deal.closing_qty = float(order_response.origin_size)
        self.active_bot.deal.closing_timestamp = round_timestamp(
            order_response.order_time
        )
        self.active_bot.status = Status.completed

        bot = self.controller.save(self.active_bot)
        bot = BotModel.model_construct(**bot.model_dump())
        self.controller.update_logs(
            bot=self.active_bot, log_message="Completed take profit."
        )

        return bot

    def switch_to_margin_short(self) -> BotModel:
        """
        Switch to short strategy.
        Doing some parts of open_deal from scratch
        this will allow us to skip one base_order and lower
        the initial buy_price.

        Because we need to create a new deal:
        1. Find base_order in the orders list as in open_deal
        2. Calculate take_profit_price and stop_loss_price as usual
        3. Create deal
        """
        self.controller.update_logs(
            "Resetting bot for margin_short strategy...", self.active_bot
        )

        # Reset bot operations
        new_bot = BotBase.model_validate(self.active_bot.model_dump())
        new_bot.strategy = Strategy.margin_short
        new_bot.logs = []

        # failure of the bot creation
        # so set status to active to be able to open_deal again
        new_bot.status = Status.inactive

        # Create new bot
        bot_table = self.controller.create(data=new_bot)

        # Activate bot
        self.active_bot = BotModel.dump_from_table(bot_table)
        margin_strategy_deal = KucoinMarginDeal(
            bot=self.active_bot, db_table=self.db_table
        )
        self.active_bot = margin_strategy_deal.margin_short_base_order()

        return self.active_bot

    def execute_stop_loss(self) -> BotModel:
        """
        Update stop limit after websocket

        - Hard sell (order status="FILLED" immediately) initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot
        """
        self.controller.update_logs("Executing stop loss...", self.active_bot)
        if isinstance(self.controller, PaperTradingTableCrud):
            qty = self.active_bot.deal.opening_qty
        else:
            qty = self.kucoin_api.get_single_spot_balance(self.symbol_info.base_asset)

        # Dispatch fake order
        if isinstance(self.controller, PaperTradingTableCrud):
            order_response, system_order = self.kucoin_api.simulate_order(
                symbol=self.active_bot.pair, side=OrderSide.sell
            )

        else:
            self.controller.update_logs(
                "Dispatching sell order for trailling profit...",
                self.active_bot,
            )
            # Dispatch real order
            order_response, system_order = self.kucoin_api.sell_order(
                symbol=self.active_bot.pair, qty=qty
            )

        price = float(system_order.price)

        stop_loss_order = OrderModel(
            timestamp=order_response.order_time,
            order_id=order_response.order_id,
            deal_type=DealType.take_profit,
            pair=system_order.symbol,
            order_side=system_order.side,
            order_type=system_order.type,
            price=price,
            qty=float(order_response.deal_size),
            time_in_force=system_order.time_in_force,
            status=order_response.status,
        )

        self.active_bot.deal.total_commissions = system_order.fee

        self.active_bot.orders.append(stop_loss_order)
        self.active_bot.deal.closing_price = price
        self.active_bot.deal.closing_qty = float(order_response.deal_size)
        self.active_bot.deal.closing_timestamp = order_response.order_time
        msg = "Completed Stop loss."
        if self.active_bot.margin_short_reversal:
            msg += " Scheduled to switch strategy"

        self.active_bot.add_log(msg)
        self.active_bot.status = Status.completed
        self.controller.save(self.active_bot)
        self.controller.update_logs("Selling quote asset...", self.active_bot)

        return self.active_bot

    def trailling_profit(self) -> BotModel | None:
        """
        Sell at take_profit price, because prices will not reach trailling
        """

        if isinstance(self.controller, PaperTradingTableCrud):
            qty = self.active_bot.deal.opening_qty
        else:
            qty = self.kucoin_api.get_single_spot_balance(self.symbol_info.base_asset)
            # Already sold?
            if qty == 0:
                self.controller.update_logs(
                    "qty=0, unable to execute trailling_profit",
                    self.active_bot,
                )
                self.active_bot.status = Status.error
                self.controller.save(self.active_bot)
                return self.active_bot

        # Dispatch fake order
        if isinstance(self.controller, PaperTradingTableCrud):
            order_response, system_order = self.kucoin_api.simulate_order(
                self.active_bot.pair,
                OrderSide.sell,
            )

        else:
            self.controller.update_logs(
                "Dispatching sell order for trailling profit...",
                self.active_bot,
            )
            # Dispatch real order
            # No price means market order
            order_response, system_order = self.kucoin_api.sell_order(
                symbol=self.active_bot.pair,
                qty=round_numbers(qty, self.qty_precision),
            )

        price = float(system_order.price)

        order_data = OrderModel(
            timestamp=order_response.order_time,
            order_id=int(order_response.order_id),
            deal_type=DealType.trailling_profit,
            pair=order_response.symbol,
            order_side=system_order.side,
            order_type=system_order.type,
            price=price,
            qty=float(system_order.orig_qty),
            time_in_force=system_order.time_in_force,
            status=order_response.status,
        )

        self.active_bot.deal.total_commissions = system_order.fee

        self.active_bot.orders.append(order_data)

        self.active_bot.deal.trailling_profit_price = float(system_order.price)
        trailling_stop_loss_price = float(system_order.price) - (
            float(system_order.price) * (self.active_bot.trailling_deviation / 100)
        )
        self.active_bot.deal.trailling_stop_loss_price = round_numbers(
            trailling_stop_loss_price, self.price_precision
        )

        # new deal parameters to replace previous
        self.active_bot.deal.closing_price = price
        self.active_bot.deal.closing_qty = float(order_response.origin_size)
        self.active_bot.deal.closing_timestamp = round_timestamp(
            order_response.order_time
        )

        self.active_bot.status = Status.completed
        self.active_bot.add_log(
            "Completed take profit after failing to break trailling"
        )
        self.controller.save(self.active_bot)

        return self.active_bot

    def streaming_updates(self, close_price: float, open_price: float):
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
            if self.active_bot.margin_short_reversal:
                if not self.symbol_info.is_margin_trading_allowed:
                    self.controller.update_logs(
                        bot=self.active_bot,
                        log_message=f"Exchange doesn't support margin trading for {self.active_bot.pair}. Cannot switch to margin short bot.",
                    )
                    return self.active_bot

                self.switch_to_margin_short()

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
                    f"Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Selling {self.active_bot.pair}",
                    self.active_bot,
                )
                self.trailling_profit()

        elif self.active_bot.take_profit > 0 and self.active_bot.deal.opening_price > 0:
            # Take profit
            if current_price >= self.active_bot.deal.take_profit_price:
                self.take_profit_order()

        return self.active_bot
