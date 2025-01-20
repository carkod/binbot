import logging
from typing import Type, Union
from database.models.bot_table import BotTable, PaperTradingTable
from database.paper_trading_crud import PaperTradingTableCrud
from tools.enum_definitions import (
    CloseConditions,
    DealType,
    OrderSide,
    Status,
    Strategy,
)
from bots.models import BotModel, OrderModel, BotBase
from deals.factory import DealAbstract
from deals.margin import MarginDeal
from tools.round_numbers import round_numbers


class SpotLongDeal(DealAbstract):
    """
    Spot (non-margin, no borrowing) long bot deal updates
    during streaming
    """

    def __init__(
        self, bot, db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable
    ) -> None:
        super().__init__(bot, db_table=db_table)
        self.active_bot: BotModel = bot
        self.db_table = db_table

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
        new_bot.status = Status.inactive
        new_bot.logs = []

        bot_table = self.controller.create(data=new_bot)
        self.active_bot = BotModel.dump_from_table(bot_table)

        margin_strategy_deal = MarginDeal(bot=self.active_bot, db_table=self.db_table)
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
            qty = self.compute_qty(self.active_bot.pair)

        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        if qty == 0:
            closed_orders = self.close_open_orders(self.active_bot.pair)
            if not closed_orders:
                order = self.verify_deal_close_order()
                if order:
                    self.active_bot.logs.append(
                        "Execute stop loss previous order found! Appending..."
                    )
                    self.active_bot.orders.append(order)
                    self.controller.save(self.active_bot)
                else:
                    self.active_bot.logs.append(
                        "No quantity in balance, no closed orders. Cannot execute update stop limit."
                    )
                    self.active_bot.status = Status.error
                    self.controller.save(self.active_bot)
                    return self.active_bot

        # Dispatch fake order
        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.simulate_order(pair=self.active_bot.pair, side=OrderSide.sell)

        else:
            self.controller.update_logs(
                "Dispatching sell order for trailling profit...",
                self.active_bot,
            )
            # Dispatch real order
            res = self.sell_order(symbol=self.active_bot.pair, qty=qty)

        stop_loss_order = OrderModel(
            timestamp=float(res["transactTime"]),
            deal_type=DealType.stop_loss,
            order_id=int(res["orderId"]),
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=float(res["price"]),
            qty=float(res["origQty"]),
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.deal.total_commissions = self.calculate_total_commissions(
            res["fills"]
        )

        self.active_bot.orders.append(stop_loss_order)
        self.active_bot.deal.closing_price = res["price"]
        self.active_bot.deal.closing_qty = res["origQty"]
        self.active_bot.deal.closing_timestamp = res["transactTime"]
        msg = "Completed Stop loss."
        if self.active_bot.margin_short_reversal:
            msg += " Scheduled to switch strategy"

        self.active_bot.logs.append(msg)
        self.active_bot.status = Status.completed
        self.controller.save(self.active_bot)

        return self.active_bot

    def trailling_profit(self) -> BotModel | None:
        """
        Sell at take_profit price, because prices will not reach trailling
        """

        if isinstance(self.controller, PaperTradingTableCrud):
            qty = self.active_bot.deal.opening_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)
            logging.error(f"trailling_profit qty: {qty}")
            # Already sold?
            if qty == 0:
                closed_orders = self.close_open_orders(self.active_bot.pair)
                if not closed_orders:
                    order = self.verify_deal_close_order()
                    if order:
                        self.active_bot.logs.append(
                            "Execute trailling profit previous order found! Appending..."
                        )
                        self.active_bot.orders.append(order)
                        self.controller.save(self.active_bot)
                    else:
                        self.active_bot.logs.append(
                            "No quantity in balance, no closed orders. Cannot execute update trailling profit."
                        )
                        self.active_bot.status = Status.error
                        self.controller.save(self.active_bot)
                    return self.active_bot

        # Dispatch fake order
        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.simulate_order(
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
            res = self.sell_order(
                symbol=self.active_bot.pair,
                qty=qty,
            )

        order_data = OrderModel(
            timestamp=res["transactTime"],
            order_id=int(res["orderId"]),
            deal_type=DealType.take_profit,
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=float(res["price"]),
            qty=float(res["origQty"]),
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.deal.total_commissions = self.calculate_total_commissions(
            res["fills"]
        )

        self.active_bot.orders.append(order_data)

        self.active_bot.deal.take_profit_price = res["price"]
        self.active_bot.deal.trailling_profit_price = res["price"]

        # to be deprecated
        self.active_bot.deal.closing_price = res["price"]
        self.active_bot.deal.closing_qty = res["origQty"]
        self.active_bot.deal.closing_timestamp = res["transactTime"]

        # new deal parameters to replace previous
        self.active_bot.deal.closing_price = float(res["price"])
        self.active_bot.deal.closing_qty = float(res["origQty"])
        self.active_bot.deal.closing_timestamp = float(res["transactTime"])

        self.active_bot.status = Status.completed
        self.active_bot.logs.append(
            f"Completed take profit after failing to break trailling {self.active_bot.pair}"
        )
        self.controller.save(self.active_bot)
        return self.active_bot

    def streaming_updates(self, close_price, open_price):
        close_price = float(close_price)
        self.close_conditions(close_price)

        self.active_bot.deal.current_price = close_price
        self.controller.save(self.active_bot)

        # Stop loss
        if (
            self.active_bot.stop_loss > 0
            and self.active_bot.deal.stop_loss_price > close_price
        ):
            self.execute_stop_loss()
            self.base_producer.update_required(self.producer, "EXECUTE_SPOT_STOP_LOSS")
            if self.active_bot.margin_short_reversal:
                self.switch_to_margin_short()
                self.base_producer.update_required(
                    self.producer, "EXECUTE_SWITCH_MARGIN_SHORT"
                )
                self.controller.update_logs(
                    "Completed switch to margin short bot", self.active_bot
                )

            return

        # Take profit trailling
        if self.active_bot.trailling and float(self.active_bot.deal.opening_price) > 0:
            # If current price didn't break take_profit (first time hitting take_profit or trailling_stop_loss lower than base_order buy_price)
            if self.active_bot.deal.trailling_stop_loss_price == 0:
                trailling_price = float(self.active_bot.deal.opening_price) * (
                    1 + (float(self.active_bot.take_profit) / 100)
                )
            else:
                # Current take profit + next take_profit
                trailling_price = float(
                    self.active_bot.deal.trailling_stop_loss_price
                ) * (1 + (float(self.active_bot.take_profit) / 100))

            self.active_bot.deal.trailling_profit_price = trailling_price
            # Direction 1 (upward): breaking the current trailling
            if close_price >= float(trailling_price):
                new_take_profit = close_price * (
                    1 + ((self.active_bot.take_profit) / 100)
                )
                new_trailling_stop_loss: float = close_price - (
                    close_price * ((self.active_bot.trailling_deviation) / 100)
                )

                # Avoid duplicate logs
                trailling_profit_price = self.active_bot.deal.trailling_profit_price

                # Update deal take_profit
                self.active_bot.deal.take_profit_price = new_take_profit
                # take_profit but for trailling, to avoid confusion
                # trailling_profit_price always be > trailling_stop_loss_price
                self.active_bot.deal.trailling_profit_price = new_take_profit

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

                if (
                    self.active_bot.deal.trailling_profit_price
                    != trailling_profit_price
                ):
                    self.active_bot.logs.append(
                        f"Updated {self.active_bot.pair} trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}"
                    )

                self.controller.save(self.active_bot)

            # Direction 2 (downward): breaking the trailling_stop_loss
            # Make sure it's red candlestick, to avoid slippage loss
            # Sell after hitting trailling stop_loss and if price already broken trailling
            if (
                float(self.active_bot.deal.trailling_stop_loss_price) > 0
                # Broken stop_loss
                and close_price < float(self.active_bot.deal.trailling_stop_loss_price)
                # Red candlestick
                and (float(open_price) > close_price)
            ):
                self.controller.update_logs(
                    f"Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Selling {self.active_bot.pair}",
                    self.active_bot,
                )
                self.trailling_profit()

        self.base_producer.update_required(
            self.producer, "EXECUTE_SPOT_STREAMING_UPDATES"
        )

    def close_conditions(self, current_price):
        """

        Check if there is a market reversal
        and close bot if so
        Get data from gainers and losers endpoint to analyze market trends
        """
        if self.active_bot.close_condition == CloseConditions.market_reversal:
            self.render_market_domination_reversal()
            if (
                self.market_domination_reversal
                and current_price < self.active_bot.deal.opening_price
            ):
                self.execute_stop_loss()
                self.base_producer.update_required(
                    self.producer, "EXECUTE_SPOT_CLOSE_CONDITION_STOP_LOSS"
                )

        pass

    def long_open_deal_trailling_parameters(self) -> BotModel:
        """
        This updates trailling parameters for spot long bots
        Once bot is activated, this section is optional.

        Inherits from old open_deal method
        this one simplifies by separating strategy specific
        """

        # Update stop loss regarless of base order
        if self.active_bot.stop_loss > 0:
            if (
                self.active_bot.strategy == Strategy.margin_short
                and self.active_bot.stop_loss > 0
            ):
                price = self.active_bot.deal.closing_price
                self.active_bot.deal.stop_loss_price = price + (
                    price * (self.active_bot.stop_loss / 100)
                )
            else:
                buy_price = float(self.active_bot.deal.opening_price)
                stop_loss_price = buy_price - (
                    buy_price * float(self.active_bot.stop_loss) / 100
                )
                self.active_bot.deal.stop_loss_price = round_numbers(
                    stop_loss_price, self.price_precision
                )

        # Keep trailling_stop_loss_price up to date in case of failure to update in autotrade
        # if we don't do this, the trailling stop loss will trigger
        if (
            self.active_bot.deal.trailling_stop_loss_price > 0
            or self.active_bot.deal.trailling_stop_loss_price
            < self.active_bot.deal.opening_price
        ):
            take_profit_price = float(self.active_bot.deal.opening_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price
            # Update trailling_stop_loss
            self.active_bot.deal.trailling_stop_loss_price = 0

        self.active_bot.status = Status.active
        self.active_bot.logs.append("Bot activated")
        self.controller.save(self.active_bot)
        return self.active_bot

    def open_deal(self):
        """
        Bot activation requires:

        1. Opening a new deal, which entails opening orders
        2. Updating stop loss and take profit
        3. Updating trailling
        4. Save in db

        - If bot DOES have a base order, we still need to update stop loss and take profit and trailling
        """
        base_order = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == DealType.base_order
            ),
            None,
        )

        if not base_order:
            self.controller.update_logs(
                f"Opening new spot deal for {self.active_bot.pair}...", self.active_bot
            )
            self.base_order()

        self.active_bot = self.long_open_deal_trailling_parameters()
        return self.active_bot
