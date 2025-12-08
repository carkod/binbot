from typing import Type, Union
from tools.maths import round_timestamp
from tools.enum_definitions import (
    DealType,
    Status,
    Strategy,
    OrderStatus,
)
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from bots.models import BotModel, OrderModel, BotBase
from exchange_apis.kucoin.deals.margin_deal import KucoinMarginDeal
from kucoin_universal_sdk.generate.margin.order.model_add_order_req import (
    AddOrderReq,
)
from exchange_apis.kucoin.deals.spot_deal import KucoinSpotDeal


class KucoinShortDeal(KucoinMarginDeal):
    """
    Short position deal implementation for Kucoin exchange.

    Happens after open_deal is executed
    formerly known as streaming updates
    these operations are triggered by websockets
    """

    def __init__(
        self, bot: BotModel, db_table: Type[Union[BotTable, PaperTradingTable]]
    ) -> None:
        super().__init__(bot=bot, db_table=db_table)
        self.active_bot: BotModel = bot
        self.symbol = self.get_symbol(self.active_bot.pair, self.active_bot.quote_asset)

    def execute_stop_loss(self) -> BotModel:
        """
        Execute stop loss when price is hit
        This is used during streaming updates
        """
        # Margin buy (buy back)
        if isinstance(self.controller, PaperTradingTableCrud):
            system_order = self.kucoin_api.simulate_margin_order(
                symbol=self.symbol, side=AddOrderReq.SideEnum.BUY
            )
        else:
            system_order = self.margin_liquidation(self.active_bot.pair)
        price = float(system_order.price)

        stop_loss_order = OrderModel(
            timestamp=int(system_order.created_at),
            deal_type=DealType.stop_loss,
            order_id=int(system_order.id),
            pair=system_order.symbol,
            order_side=system_order.side,
            order_type=system_order.type,
            price=price,
            qty=float(system_order.size),
            time_in_force=system_order.time_in_force,
            status=OrderStatus.FILLED if system_order.active else OrderStatus.EXPIRED,
        )

        self.active_bot.deal.total_commissions = system_order.fee

        self.active_bot.orders.append(stop_loss_order)

        self.active_bot.deal.closing_price = float(price)
        self.active_bot.deal.closing_qty = float(system_order.size)
        self.active_bot.deal.closing_timestamp = round_timestamp(
            system_order.created_at
        )

        self.active_bot.status = Status.completed
        self.active_bot.add_log("Completed Stop loss order")

        self.controller.save(self.active_bot)

        return self.active_bot

    def execute_take_profit(
        self, take_profit_type: DealType = DealType.take_profit
    ) -> BotModel:
        """
        Execute take profit when price is hit.
        This can be a simple take_profit order when take_profit_price is hit or
        a trailling_stop_loss when trailling_stop_loss_price is hit.
        This is because the only difference is the price and the price either provided
        by whatever triggers this sell or if not provided the matching_engine will provide it.

        This also sits well with the concept of "taking profit", which is closing a position at profit.

        - Buy back asset sold
        """
        # Margin buy (buy back)
        if isinstance(self.controller, PaperTradingTableCrud):
            system_order = self.kucoin_api.simulate_margin_order(
                self.active_bot.pair, AddOrderReq.SideEnum.BUY
            )
        else:
            self.controller.update_logs("Attempting to liquidate loan", self.active_bot)
            system_order = self.margin_liquidation(self.active_bot.pair)

        price = float(system_order.price)

        # No res means it wasn't properly closed/completed
        take_profit_order = OrderModel(
            timestamp=system_order.created_at,
            deal_type=take_profit_type,
            order_id=int(system_order.id),
            pair=system_order.symbol,
            order_side=system_order.side,
            order_type=system_order.type,
            price=price,
            qty=float(system_order.size),
            time_in_force=system_order.time_in_force,
            status=OrderStatus.FILLED if system_order.active else OrderStatus.EXPIRED,
        )

        self.active_bot.deal.total_commissions = system_order.fee

        self.active_bot.orders.append(take_profit_order)
        self.active_bot.deal.closing_price = price
        self.active_bot.deal.closing_timestamp = round_timestamp(
            system_order.created_at
        )
        self.active_bot.deal.closing_qty = float(system_order.size)
        self.active_bot.add_log("Completed Take profit!")
        self.active_bot.status = Status.completed

        self.controller.save(self.active_bot)

        return self.active_bot

    def switch_to_long_bot(self) -> BotModel:
        """
        Switch to long strategy.
        Doing some parts of open_deal from scratch
        this will allow us to skip one base_order and lower
        the initial buy_price

        Use open_deal as reference to create this new long bot deal:
        1. Find base_order in the orders list as in open_deal
        2. Calculate take_profit_price and stop_loss_price as usual
        3. Create deal
        """
        self.controller.update_logs(
            "Switching margin_short to long strategy", self.active_bot
        )

        # Create new bot as you'd do through Dashboard terminal
        new_bot = BotBase.model_validate(self.active_bot.model_dump())
        new_bot.strategy = Strategy.long
        new_bot.logs = []

        # margin bot fund liquidation and network request can cause
        # failure of the bot creation
        # so set status to active to be able to open_deal again
        new_bot.status = Status.active

        # Create new bot
        created_bot = self.controller.create(new_bot)
        bot_model = BotModel.model_validate(created_bot.model_dump())
        spot_deal = KucoinSpotDeal(bot=bot_model, db_table=self.db_table)

        # to avoid circular imports make network request
        # This class is already imported for switch_to_margin_short
        bot_id = spot_deal.open_deal()
        self.controller.update_logs(
            f"Switched margin_short to long strategy. New bot id: {bot_id}",
            self.active_bot,
        )
        return self.active_bot

    def update_trailling_profit(self, close_price: float) -> BotModel:
        # Direction 1: downward trend (short)
        if self.active_bot.deal.trailling_stop_loss_price == 0:
            price = (
                close_price
                if close_price < self.active_bot.deal.opening_price
                else self.active_bot.deal.opening_price
            )
            trailling_take_profit = price - (
                price * ((self.active_bot.take_profit) / 100)
            )
            stop_loss_trailling_price = trailling_take_profit - (
                trailling_take_profit * ((self.active_bot.trailling_deviation) / 100)
            )
            # If trailling_stop_loss is above (margin) the opening_price do not update trailling stop loss, because it'll close at a loss
            # stop_loss is the safe net in this case
            if stop_loss_trailling_price < self.active_bot.deal.opening_price:
                self.active_bot.deal.trailling_stop_loss_price = (
                    stop_loss_trailling_price
                )
                self.active_bot.add_log(
                    f"{self.active_bot.pair} below opening_price, setting trailling_stop_loss (margin_short)"
                )
                self.controller.save(self.active_bot)

        # Keep trailling_stop_loss up to date
        if (
            self.active_bot.deal.trailling_stop_loss_price > 0
            and self.active_bot.deal.trailling_profit_price > 0
            and self.active_bot.deal.trailling_stop_loss_price
            < self.active_bot.deal.closing_price
        ):
            self.active_bot.deal.trailling_stop_loss_price = (
                self.active_bot.deal.trailling_profit_price
                * (1 + ((self.active_bot.trailling_deviation) / 100))
            )

            # Reset stop_loss_price to avoid confusion in front-end
            self.active_bot.deal.stop_loss_price = 0
            self.controller.update_logs(
                f"{self.active_bot.pair} Updating after broken first trailling_profit (short)",
                self.active_bot,
            )

        # Direction 1 (downward): breaking the current trailling
        if close_price <= self.active_bot.deal.trailling_profit_price:
            new_take_profit: float = close_price - (
                close_price * (self.active_bot.take_profit / 100)
            )
            new_trailling_stop_loss = close_price * (
                1 + (self.active_bot.trailling_deviation / 100)
            )
            # Update deal trailling profit
            self.active_bot.deal.trailling_profit_price = new_take_profit

            # Update trailling_stop_loss
            if new_trailling_stop_loss < self.active_bot.deal.closing_price:
                # Selling below buy_price will cause a loss
                # instead let it drop until it hits safety order or stop loss
                # Update trailling_stop_loss
                self.active_bot.deal.trailling_stop_loss_price = new_trailling_stop_loss

        self.controller.save(self.active_bot)

        return self.active_bot

    def streaming_updates(self, close_price: float, open_price: float = 0) -> BotModel:
        """
        Margin_short streaming updates

        open_price is unused, but kept for interface consistency
        """

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
                    self.kucoin_api.cancel_margin_order_by_order_id(
                        symbol=self.symbol, order_id=d.order_id
                    )

        # Sell everything
        balance = self.get_isolated_balance()
        if balance:
            if isinstance(self.controller, PaperTradingTableCrud):
                system_order = self.kucoin_api.simulate_margin_order(
                    symbol=self.symbol, side=AddOrderReq.SideEnum.BUY
                )
            else:
                system_order = self.margin_liquidation(self.active_bot.pair)

            price = float(system_order.price)

            if system_order:
                order = OrderModel(
                    timestamp=int(system_order.created_at),
                    deal_type=DealType.panic_close,
                    order_id=int(system_order.id),
                    pair=system_order.symbol,
                    order_side=system_order.side,
                    order_type=system_order.type,
                    price=price,
                    qty=float(system_order.size),
                    time_in_force=system_order.time_in_force,
                    status=OrderStatus.FILLED
                    if system_order.active
                    else OrderStatus.EXPIRED,
                )

                self.active_bot.deal.total_commissions = system_order.fee

                self.active_bot.orders.append(order)

                self.active_bot.deal.closing_price = price
                self.active_bot.deal.closing_qty = float(system_order.size)
                self.active_bot.deal.closing_timestamp = round_timestamp(
                    system_order.created_at
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
