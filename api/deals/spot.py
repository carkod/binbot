import logging

from base_producer import BaseProducer
from deals.base import BaseDeal
from deals.margin import MarginDeal
from deals.models import BinanceOrderModel
from tools.enum_definitions import CloseConditions, DealType, Status, Strategy
from bots.schemas import BotSchema


class SpotLongDeal(BaseDeal):
    """
    Spot (non-margin, no borrowing) long bot deal updates
    during streaming
    """

    def __init__(self, bot, db_collection_name: str) -> None:
        # Inherit from parent class
        self.db_collection_name = db_collection_name
        super().__init__(bot, db_collection_name)
        self.base_producer = BaseProducer()
        self.producer = self.base_producer.start_producer()
        self.active_bot: BotSchema

    def switch_margin_short(self):
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
        self.update_deal_logs(
            "Resetting bot for margin_short strategy...", self.active_bot
        )
        self.active_bot.strategy = Strategy.margin_short
        self.active_bot = self.create_new_bot_streaming(active_bot=self.active_bot)

        self.active_bot = MarginDeal(
            bot=self.active_bot, db_collection_name=self.db_collection_name
        ).margin_short_base_order()

        self.active_bot = self.save_bot_streaming(self.active_bot)
        return self.active_bot

    def execute_stop_loss(self):
        """
        Update stop limit after websocket

        - Hard sell (order status="FILLED" immediately) initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot
        """
        self.update_deal_logs("Executing stop loss...", self.active_bot)
        if self.db_collection.name == "paper_trading":
            qty = self.active_bot.deal.buy_total_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)

        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        if not qty:
            closed_orders = self.close_open_orders(self.active_bot.pair)
            if not closed_orders:
                order = self.verify_deal_close_order()
                if order:
                    self.active_bot.errors.append(
                        "Execute stop loss previous order found! Appending..."
                    )
                    self.active_bot.orders.append(order)
                else:
                    self.update_deal_logs(
                        "No quantity in balance, no closed orders. Cannot execute update stop limit.",
                        self.active_bot,
                    )
                    self.active_bot.status = Status.error
                    self.active_bot = self.save_bot_streaming(self.active_bot)
                    return

        # Dispatch fake order
        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(self.active_bot.pair, qty, "SELL")

        else:
            self.active_bot.errors.append(
                "Dispatching sell order for trailling profit..."
            )
            # Dispatch real order
            res = self.sell_order(symbol=self.active_bot.pair, qty=qty)

        stop_loss_order = BinanceOrderModel(
            timestamp=res["transactTime"],
            deal_type=DealType.stop_loss,
            order_id=int(res["orderId"]),
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res["price"],
            qty=float(res["origQty"]),
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.total_commission = self.calculate_total_commissions(
            res["fills"]
        )

        self.active_bot.orders.append(stop_loss_order)
        self.active_bot.deal.sell_price = res["price"]
        self.active_bot.deal.sell_qty = res["origQty"]
        self.active_bot.deal.sell_timestamp = res["transactTime"]
        msg = "Completed Stop loss. "
        if self.active_bot.margin_short_reversal:
            msg += "Scheduled to switch strategy"
        self.active_bot.errors.append(msg)
        self.active_bot.status = Status.completed

        self.active_bot = self.save_bot_streaming(self.active_bot)
        return self.active_bot

    def trailling_profit(self) -> BotSchema | None:
        """
        Sell at take_profit price, because prices will not reach trailling
        """

        price = self.active_bot.deal.trailling_stop_loss_price

        if self.db_collection.name == "paper_trading":
            qty = self.active_bot.deal.buy_total_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)
            # Already sold?
            if not qty:
                closed_orders = self.close_open_orders(self.active_bot.pair)
                if not closed_orders:
                    order = self.verify_deal_close_order()
                    if order:
                        self.active_bot.errors.append(
                            "Execute trailling profit previous order found! Appending..."
                        )
                        self.active_bot.orders.append(order)
                    else:
                        self.update_deal_logs(
                            "No quantity in balance, no closed orders. Cannot execute update trailling profit.",
                            self.active_bot,
                        )
                        self.active_bot.status = Status.error
                        self.active_bot = self.save_bot_streaming(self.active_bot)
                    return self.active_bot

        # Dispatch fake order
        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(
                self.active_bot.pair,
                price,
                qty,
                "SELL",
            )

        else:
            self.active_bot.errors.append(
                "Dispatching sell order for trailling profit..."
            )
            # Dispatch real order
            # No price means market order
            res = self.sell_order(
                symbol=self.active_bot.pair,
                qty=qty,
            )

        order_data = BinanceOrderModel(
            timestamp=res["transactTime"],
            order_id=res["orderId"],
            deal_type=DealType.take_profit,
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res["price"],
            qty=res["origQty"],
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.total_commission = self.calculate_total_commissions(
            res["fills"]
        )

        self.active_bot.orders.append(order_data)

        self.active_bot.deal.take_profit_price = res["price"]
        self.active_bot.deal.trailling_profit_price = res["price"]
        self.active_bot.deal.sell_price = res["price"]
        self.active_bot.deal.sell_qty = res["origQty"]
        self.active_bot.deal.sell_timestamp = res["transactTime"]
        self.active_bot.status = Status.completed
        msg = f"Completed take profit after failing to break trailling {self.active_bot.pair}"
        self.active_bot.errors.append(msg)

        self.active_bot = self.save_bot_streaming(self.active_bot)
        return self.active_bot

    def streaming_updates(self, close_price, open_price):
        close_price = float(close_price)
        self.close_conditions(float(close_price))

        self.active_bot.deal.current_price = close_price
        self.active_bot = self.save_bot_streaming(self.active_bot)

        # Stop loss
        if float(self.active_bot.stop_loss) > 0 and float(
            self.active_bot.deal.stop_loss_price
        ) > float(close_price):
            self.execute_stop_loss()
            self.base_producer.update_required(self.producer, "EXECUTE_SPOT_STOP_LOSS")
            if self.active_bot.margin_short_reversal:
                self.switch_margin_short()
                self.base_producer.update_required(
                    self.producer, "EXECUTE_SWITCH_MARGIN_SHORT"
                )
                self.update_deal_logs(
                    "Completed switch to margin short bot", self.active_bot
                )

            return

        # Take profit trailling
        if (self.active_bot.trailling) and float(self.active_bot.deal.buy_price) > 0:
            # If current price didn't break take_profit (first time hitting take_profit or trailling_stop_loss lower than base_order buy_price)
            if self.active_bot.deal.trailling_stop_loss_price == 0:
                trailling_price = float(self.active_bot.deal.buy_price) * (
                    1 + (float(self.active_bot.take_profit) / 100)
                )
            else:
                # Current take profit + next take_profit
                trailling_price = float(
                    self.active_bot.deal.trailling_stop_loss_price
                ) * (1 + (float(self.active_bot.take_profit) / 100))

            self.active_bot.deal.trailling_profit_price = trailling_price
            # Direction 1 (upward): breaking the current trailling
            if float(close_price) >= float(trailling_price):
                new_take_profit = float(close_price) * (
                    1 + (float(self.active_bot.take_profit) / 100)
                )
                new_trailling_stop_loss = float(close_price) - (
                    float(close_price)
                    * (float(self.active_bot.trailling_deviation) / 100)
                )
                # Update deal take_profit
                self.active_bot.deal.take_profit_price = new_take_profit
                # take_profit but for trailling, to avoid confusion
                # trailling_profit_price always be > trailling_stop_loss_price
                self.active_bot.deal.trailling_profit_price = new_take_profit

                if (
                    new_trailling_stop_loss > self.active_bot.deal.buy_price
                    and new_trailling_stop_loss
                    > self.active_bot.deal.trailling_stop_loss_price
                ):
                    # Selling below buy_price will cause a loss
                    # instead let it drop until it hits safety order or stop loss
                    # Update trailling_stop_loss
                    self.active_bot.deal.trailling_stop_loss_price = (
                        new_trailling_stop_loss
                    )

                self.update_deal_logs(
                    f"Updated {self.active_bot.pair} trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}",
                    self.active_bot,
                )
                self.active_bot = self.save_bot_streaming(self.active_bot)

            # Direction 2 (downward): breaking the trailling_stop_loss
            # Make sure it's red candlestick, to avoid slippage loss
            # Sell after hitting trailling stop_loss and if price already broken trailling
            if (
                float(self.active_bot.deal.trailling_stop_loss_price) > 0
                # Broken stop_loss
                and float(close_price)
                < float(self.active_bot.deal.trailling_stop_loss_price)
                # Red candlestick
                and (float(open_price) > float(close_price))
            ):
                self.update_deal_logs(
                    f"Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Selling {self.active_bot.pair}",
                    self.active_bot,
                )
                self.trailling_profit()
                self.base_producer.update_required(
                    self.producer, "EXECUTE_SPOT_TRAILLING_PROFIT"
                )

        # Update unfilled orders
        unupdated_order = next(
            (
                deal
                for deal in self.active_bot.orders
                if deal.deal_type == "NEW" or deal.price == 0
            ),
            None,
        )
        if unupdated_order:
            order_response = self.get_all_orders(
                self.active_bot.pair, unupdated_order.order_id
            )
            logging.info(f"Unfilled orders response{order_response}")
            if order_response[0]["status"] == "FILLED":
                for i, order in enumerate(self.active_bot.orders):
                    if order.order_id == order_response["orderId"]:
                        self.active_bot.orders[i].price = order_response["price"]
                        self.active_bot.orders[i].qty = order_response["origQty"]
                        self.active_bot.orders[i].status = order_response["status"]

            self.active_bot = self.save_bot_streaming(self.active_bot)

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
                and current_price < self.active_bot.deal.buy_price
            ):
                self.execute_stop_loss()
                self.base_producer.update_required(
                    self.producer, "EXECUTE_SPOT_CLOSE_CONDITION_STOP_LOSS"
                )

        pass
