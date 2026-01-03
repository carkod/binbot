from typing import Type, Union
from databases.crud.autotrade_crud import AutotradeCrud
from databases.tables.bot_table import BotTable, PaperTradingTable
from bots.models import BotModel, OrderModel
from pybinbot import (
    DealType,
    Status,
    OrderSide,
    OrderStatus,
    round_numbers,
    round_timestamp,
)
from exchange_apis.binance.deals.spot_deal import BinanceSpotDeal
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from tools.exceptions import BinanceErrors


class LongDeal(BinanceSpotDeal):
    """
    Long deals are Binbot deals made using a long strategy: buy low, sell high.

    They use the Exchange's SPOT market, so it would be using the spot adaptation of Binance APIs, thus inheriting from BinanceSpotDeal.
    """

    def __init__(
        self, bot, db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable
    ) -> None:
        super().__init__(bot, db_table=db_table)
        self.autotrade_settings = AutotradeCrud().get_settings()
        self.active_bot: BotModel = bot

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

    def streaming_updates(self, current_price: float, open_price: float):
        self.check_failed_switch_long_bot()
        self.close_conditions(current_price)

        self.active_bot.deal.current_price = current_price
        self.controller.save(self.active_bot)

        # Update orders if not filled
        self.update_spot_orders()

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

    def close_all(self) -> BotModel:
        """
        Close all deals and sell pair
        1. Close all deals
        2. Sell Coins
        3. Delete bot
        """
        orders = self.active_bot.orders

        # Close all active orders
        if isinstance(self.controller, PaperTradingTableCrud) and len(orders) > 0:
            for d in orders:
                if (
                    d.status == OrderStatus.NEW
                    or d.status == OrderStatus.PARTIALLY_FILLED
                ):
                    self.controller.update_logs(
                        "Failed to close all active orders (status NEW), retrying...",
                        self.active_bot,
                    )
                    self.replace_order(d.order_id)

        # Sell everything
        pair = self.active_bot.pair
        base_asset = self.symbols_crud.base_asset(pair)
        balance = self.get_single_spot_balance(base_asset)
        if balance > 0:
            qty = round_numbers(balance, self.qty_precision)
        else:
            self.active_bot.status = Status.error
            self.active_bot.add_log("No balance found. Skipping panic sell")

        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.simulate_order(
                pair=self.active_bot.pair,
                side=OrderSide.sell,
            )
        else:
            try:
                res = self.sell_order(symbol=self.active_bot.pair, qty=qty)
                price = float(res["price"])
                if price == 0:
                    price = self.calculate_avg_price(res["fills"])

                order_data = OrderModel(
                    timestamp=int(res["transactTime"]),
                    order_id=res["orderId"],
                    deal_type=DealType.take_profit,
                    pair=res["symbol"],
                    order_side=res["side"],
                    order_type=res["type"],
                    price=price,
                    qty=float(res["origQty"]),
                    time_in_force=res["timeInForce"],
                    status=res["status"],
                )

                self.active_bot.orders.append(order_data)
                self.active_bot.deal.closing_price = price
                self.active_bot.deal.closing_qty = float(res["origQty"])
                self.active_bot.deal.closing_timestamp = round_timestamp(
                    res["transactTime"]
                )
                self.active_bot.add_log(
                    "Panic sell triggered. All active orders closed"
                )
                self.active_bot.status = Status.completed
                self.controller.save(self.active_bot)

            except BinanceErrors as error:
                if error.code == -1013:
                    # This probs means qty is too low to sell_order
                    # we can ignore because the cronjob will clean dust
                    # continue execution to clean quote asset
                    pass

        self.active_bot = self.sell_quote_asset()

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
        base_order = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == DealType.base_order
            ),
            None,
        )

        if not base_order:
            if not self.symbol_info.is_margin_trading_allowed:
                self.active_bot.margin_short_reversal = False
                self.active_bot.add_log(
                    "Auto short bot reversal disabled. Exchange doesn't support margin trading for this pair."
                )

            self.controller.update_logs(
                f"Opening new spot deal for {self.active_bot.pair}...", self.active_bot
            )
            self.controller.save(self.active_bot)
            self.base_order()

        if (
            self.active_bot.status == Status.active
            or self.active_bot.deal.opening_price > 0
        ):
            # Update bot no activation required
            self.active_bot = self.long_update_deal_trailling_parameters()
        else:
            # Activation required
            self.active_bot = self.long_open_deal_trailling_parameters()

        self.controller.save(self.active_bot)
        return self.active_bot
