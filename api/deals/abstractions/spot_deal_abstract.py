import logging
from typing import Type, Union
from databases.models.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from tools.enum_definitions import (
    CloseConditions,
    DealType,
    OrderSide,
    Status,
    Strategy,
    OrderStatus,
)
from bots.models import BotModel, OrderModel, BotBase
from deals.abstractions.factory import DealAbstract
from deals.margin import MarginDeal
from tools.round_numbers import round_numbers, round_timestamp
from urllib.error import HTTPError


class SpotDealAbstract(DealAbstract):
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
        self, bot, db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable
    ) -> None:
        super().__init__(bot, db_table=db_table)
        self.active_bot: BotModel = bot
        self.db_table = db_table
        self.symbols_crud = SymbolsCrud()

    def update_spot_orders(self) -> BotModel:
        """
        Keeps self.active_bot.orders up to date
        as they often don't fullfill immediately

        Used by streaming_controller
        """
        for order in self.active_bot.orders:
            if order.status == OrderStatus.NEW:
                try:
                    self.delete_order(
                        symbol=self.active_bot.pair, order_id=order.order_id
                    )
                except HTTPError:
                    # No order to cancel
                    self.controller.update_logs(
                        f"Can't find order {order.order_id}", self.active_bot
                    )
                    pass

                if order.order_side == OrderSide.buy:
                    res = self.buy_order(symbol=self.active_bot.pair, qty=order.qty)
                else:
                    res = self.sell_order(symbol=self.active_bot.pair, qty=order.qty)

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

        price = float(res["price"])
        if price == 0:
            price = self.calculate_avg_price(res["fills"])

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
        self.active_bot.deal.closing_timestamp = round_timestamp(res["transactTime"])
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
                qty=round_numbers(qty, self.qty_precision),
            )

        price = float(res["price"])
        if price == 0:
            price = self.calculate_avg_price(res["fills"])

        order_data = OrderModel(
            timestamp=res["transactTime"],
            order_id=int(res["orderId"]),
            deal_type=DealType.trailling_profit,
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

        self.active_bot.deal.trailling_profit_price = float(res["price"])
        self.active_bot.deal.trailling_stop_loss_price = round_numbers(
            float(res["price"])
            - (float(res["price"]) * (self.active_bot.trailling_deviation / 100))
        )

        # new deal parameters to replace previous
        self.active_bot.deal.closing_price = price
        self.active_bot.deal.closing_qty = float(res["origQty"])
        self.active_bot.deal.closing_timestamp = round_timestamp(res["transactTime"])

        self.active_bot.status = Status.completed
        self.active_bot.logs.append(
            "Completed take profit after failing to break trailling"
        )

        self.controller.save(self.active_bot)
        return self.active_bot

    def close_conditions(self, current_price):
        """

        Check if there is a market reversal
        and close bot if so
        Get data from gainers and losers endpoint to analyze market trends
        """
        if self.active_bot.close_condition == CloseConditions.market_reversal:
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
        Once bot is activated.

        Inherits from old open_deal method
        this one simplifies by separating strategy specific
        """

        if self.active_bot.strategy == Strategy.margin_short:
            logging.error("Bot executing wrong long_open_deal_trailling_parameters")
            return self.active_bot

        # Update stop loss regarless of base order
        if self.active_bot.stop_loss > 0:
            price = self.active_bot.deal.opening_price
            self.active_bot.deal.stop_loss_price = price + (
                price * (self.active_bot.stop_loss / 100)
            )

        # Keep trailling_stop_loss_price up to date in case of failure to update in autotrade
        # if we don't do this, the trailling stop loss will trigger
        if self.active_bot.trailling:
            trailling_profit = float(self.active_bot.deal.opening_price) * (
                1 + (float(self.active_bot.trailling_profit) / 100)
            )
            self.active_bot.deal.trailling_profit_price = trailling_profit
            # Reset trailling stop loss
            # this should be updated during streaming
            self.active_bot.deal.trailling_stop_loss_price = 0
            # Old property fix
            self.active_bot.deal.take_profit_price = 0

        else:
            # No trailling so only update take_profit
            take_profit_price = float(self.active_bot.deal.opening_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price

        self.active_bot.status = Status.active
        self.active_bot.logs.append("Bot activated")
        self.controller.save(self.active_bot)
        return self.active_bot

    def long_update_deal_trailling_parameters(self) -> BotModel:
        """
        Same as long_open_deal_trailling_parameters
        but when clicked on "update deal".

        This makes sure deal trailling values are up to date and
        not out of sync with the bot parameters
        """

        if self.active_bot.strategy == Strategy.margin_short:
            logging.error("Bot executing wrong long_update_deal_trailling_parameters")
            return self.active_bot

        if self.active_bot.stop_loss > 0:
            buy_price = self.active_bot.deal.opening_price
            stop_loss_price = buy_price - (
                buy_price * (self.active_bot.stop_loss / 100)
            )
            self.active_bot.deal.stop_loss_price = round_numbers(
                stop_loss_price, self.price_precision
            )

        if (
            self.active_bot.trailling
            and self.active_bot.trailling_deviation > 0
            and self.active_bot.trailling_profit > 0
        ):
            trailling_profit_price = float(self.active_bot.deal.opening_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.trailling_profit_price = round_numbers(
                trailling_profit_price, self.price_precision
            )

            if self.active_bot.deal.trailling_stop_loss_price != 0:
                # trailling_stop_loss_price should be updated during streaming
                # This resets it after "Update deal" because parameters have changed
                self.active_bot.deal.trailling_stop_loss_price = 0

        return self.active_bot
