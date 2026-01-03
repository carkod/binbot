from typing import Type, Union
from databases.crud.autotrade_crud import AutotradeCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from pybinbot.enum import DealType, OrderSide, OrderStatus
from bots.models import BotModel, OrderModel
from pybinbot.enum import Status
from tools.exceptions import BinanceErrors
from pybinbot.maths import (
    round_timestamp,
)
from exchange_apis.binance.deals.margin_deal import BinanceMarginDeal


class BinanceShortDeal(BinanceMarginDeal):
    """
    Short deals are Binbot deals made using a short strategy: sell high, buy low.

    They use the Exchange's MARGIN ISOLATED market, so it would be using the margin adaptation of Binance APIs, thus inheriting from BinanceMarginDeal.

    - streaming_updates: updates for market_updates bot streaming
    - close_all: deactivation, panic close, quick liquidation
    - open_deal: main way to activate bots, used by dashaboard and binquant
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ):
        super().__init__(bot, db_table=db_table)
        self.active_bot = bot
        self.db_table = db_table
        self.autotrade_settings = AutotradeCrud().get_settings()

    def check_failed_switch_long_bot(self) -> BotModel:
        """
        Check if switch to long bot failed
        reactivate/reopen if failed
        """
        if (
            self.active_bot.status == Status.active
            and self.active_bot.deal.opening_qty == 0
        ):
            self.active_bot.add_log(
                "Switch to long possibly failed. Reopening margin short bot."
            )
            self.open_deal()
            self.controller.save(self.active_bot)

        return self.active_bot

    def streaming_updates(self, close_price: float, open_price: float = 0) -> BotModel:
        """
        Margin_short streaming updates

        open_price is unused, but kept for interface consistency
        """

        # Check for switch to long bot that failed
        self.active_bot = self.check_failed_switch_long_bot()

        self.close_conditions(close_price)

        self.active_bot.deal.current_price = close_price
        # Make sure current price is up to date
        self.controller.save(self.active_bot)

        if self.active_bot.deal.stop_loss_price == 0:
            self.active_bot.deal.stop_loss_price = (
                self.active_bot.deal.opening_price
                + (
                    self.active_bot.deal.opening_price
                    * (self.active_bot.stop_loss / 100)
                )
            )

        # Direction 3: upward trend (short)
        # Breaking trailling_stop_loss, sell for safety
        if close_price > self.active_bot.deal.stop_loss_price:
            self.controller.update_logs(
                f"Executing margin_short stop_loss reversal after hitting stop_loss_price {self.active_bot.deal.stop_loss_price}",
                self.active_bot,
            )
            self.execute_stop_loss()
            if self.active_bot.margin_short_reversal:
                if not self.symbol_info.is_margin_trading_allowed:
                    self.active_bot.add_log(
                        f"Margin trading not allowed for {self.active_bot.pair}. Cannot switch to long bot."
                    )
                    self.controller.save(self.active_bot)
                    return self.active_bot

                self.switch_to_long_bot()

            self.controller.save(self.active_bot)

        if (
            close_price > 0
            and self.active_bot.trailling
            and self.active_bot.trailling_profit > 0
            and self.active_bot.trailling_deviation > 0
        ):
            # Direction 1.1: downward trend (short)
            # Breaking trailling
            # Trailling only to update when it's above opening_price
            if close_price < self.active_bot.deal.trailling_profit_price:
                self.update_trailling_profit(close_price)

            # Direction 2: upward trend (short). breaking the trailling_stop_loss
            # Make sure it's red candlestick, to avoid slippage loss
            # Sell after hitting trailling stop_loss and if price already broken trailling
            if close_price > self.active_bot.deal.trailling_stop_loss_price:
                self.controller.update_logs(
                    f"Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Selling {self.active_bot.pair}",
                    self.active_bot,
                )
                # since price is given by matching engine
                self.execute_take_profit(DealType.trailling_profit)

        if not self.active_bot.trailling and self.active_bot.deal.take_profit_price > 0:
            # Not a trailling bot, just simple take profit
            if close_price <= self.active_bot.deal.take_profit_price:
                self.controller.update_logs(
                    f"Executing margin_short take_profit after hitting take_profit_price {self.active_bot.deal.take_profit_price}",
                    self.active_bot,
                )
                self.execute_take_profit()

        return self.active_bot

    def close_all(self) -> BotModel:
        """
        Deactivation + liquidation of loans

        1. Close all orders if there any are still opened
        2. Terminate margin deal (repay loan, sell assets, transfer funds back to SPOT)
        3. Update bot status to completed
        """
        orders = self.active_bot.orders

        # Close all active orders
        if len(orders) > 0:
            for d in orders:
                if (
                    d.status == OrderStatus.NEW
                    or d.status == OrderStatus.PARTIALLY_FILLED
                ):
                    self.controller.update_logs(
                        "Failed to close all active orders (status NEW), retrying...",
                        self.active_bot,
                    )
                    try:
                        self.cancel_margin_order(
                            symbol=self.active_bot.pair, order_id=int(d.order_id)
                        )
                    except BinanceErrors:
                        break

        # Sell everything
        base_asset = self.symbols_crud.base_asset(self.active_bot.pair)
        balance = self.get_single_raw_balance(base_asset)
        if balance > 0:
            if isinstance(self.controller, PaperTradingTableCrud):
                res = self.simulate_margin_order(self.active_bot.pair, OrderSide.buy)
            else:
                res = self.margin_liquidation(self.active_bot.pair)

            price = float(res["price"])
            if price == 0:
                price = self.calculate_avg_price(res["fills"])

            if res:
                order = OrderModel(
                    timestamp=int(res["transactTime"]),
                    deal_type=DealType.panic_close,
                    order_id=int(res["orderId"]),
                    pair=res["symbol"],
                    order_side=res["side"],
                    order_type=res["type"],
                    price=price,
                    qty=float(res["origQty"]),
                    time_in_force=res["timeInForce"],
                    status=res["status"],
                )

                self.active_bot.deal.total_commissions += (
                    self.calculate_total_commissions(res["fills"])
                )

                self.active_bot.orders.append(order)

                self.active_bot.deal.closing_price = price
                self.active_bot.deal.closing_qty = float(res["origQty"])
                self.active_bot.deal.closing_timestamp = round_timestamp(
                    res["transactTime"]
                )

                self.active_bot.add_log("Completed Stop loss order")
                self.active_bot.status = Status.completed
            else:
                self.active_bot.status = Status.error
                self.active_bot.add_log("Unable to complete stop loss")

        else:
            self.active_bot.status = Status.error
            self.active_bot.add_log("No balance found. Skipping panic sell")

        self.controller.save(self.active_bot)
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
