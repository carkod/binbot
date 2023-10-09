import logging

from deals.base import BaseDeal
from requests.exceptions import HTTPError
from deals.models import BinanceOrderModel
from tools.handle_error import (
    NotEnoughFunds,
    encode_json,
)
from tools.exceptions import (
    TraillingProfitError,
)
from tools.round_numbers import round_numbers, supress_notation
from pydantic import ValidationError
from tools.enum_definitions import Status
from deals.margin import MarginDeal
from datetime import datetime
from bots.schemas import BotSchema
from tools.exceptions import TerminateStreaming


class SpotLongDeal(BaseDeal):
    """
    Spot (non-margin, no borrowing) long bot deal updates
    during streaming
    """
    def __init__(self, bot, db_collection_name: str) -> None:
        # Inherit from parent class
        super().__init__(bot, db_collection_name)
    
    def switch_margin_short(self, close_price):
        msg = "Resetting bot for margin_short strategy..."
        self.update_deal_logs(msg)
        self.save_bot_streaming()

        self.active_bot = MarginDeal(self.active_bot, db_collection_name="bots").margin_short_base_order()
        self.save_bot_streaming()


    def execute_stop_loss(self, price):
        """
        Update stop limit after websocket
        - Hard sell (order status="FILLED" immediately) initial amount crypto in deal
        - Close current opened take profit order
        - Deactivate bot
        """
        if self.db_collection.name == "paper_trading":
            qty = self.active_bot.deal.buy_total_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)

        # If for some reason, the bot has been closed already (e.g. transacted on Binance)
        # Inactivate bot
        if not qty:
            closed_orders = self.close_open_orders(self.active_bot.pair)
            if not closed_orders:
                self.update_deal_logs(
                    f"No quantity in balance, no closed orders. Cannot execute update stop limit."
                )
                self.active_bot.status = Status.error
                self.save_bot_streaming()
                return

        order_id = None
        for order in self.active_bot.orders:
            if order.deal_type == "take_profit":
                order_id = order.order_id
                self.active_bot.orders.remove(order)
                break

        if order_id:
            try:
                # First cancel old order to unlock balance
                self.bb_request(
                    f"{self.bb_close_order_url}/{self.active_bot.pair}/{order_id}",
                    "DELETE",
                )
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs("Take profit order not found, no need to cancel")
                return

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(self.active_bot.pair, price, qty, "SELL")
        else:
            try:
                res = self.sell_order(symbol=self.active_bot.pair, qty=qty, price=price)
            except Exception as error:
                self.update_deal_logs(
                    f"Error trying to open new stop_limit order {error}"
                )
                return

        stop_loss_order = BinanceOrderModel(
            timestamp=res["transactTime"],
            deal_type="stop_loss",
            order_id=res["orderId"],
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res["price"],
            qty=res["origQty"],
            fills=res["fills"],
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        for chunk in res["fills"]:
            self.active_bot.total_commission += float(chunk["commission"])

        self.active_bot.orders.append(stop_loss_order)
        self.active_bot.deal.sell_price = res["price"]
        self.active_bot.deal.sell_qty = res["origQty"]
        self.active_bot.deal.sell_timestamp = res["transactTime"]
        msg = f"Completed Stop loss"
        self.active_bot.errors.append(msg)
        self.active_bot.status = Status.completed

        bot = self.save_bot_streaming()
        return bot

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
                    self.update_deal_logs(
                        f"No quantity in balance, no closed orders. Cannot execute update trailling profit."
                    )
                    self.active_bot.status = Status.error
                    bot = self.save_bot_streaming()
                    return bot

        # Dispatch fake order
        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(
                self.active_bot.pair,
                price,
                qty,
                "SELL",
            )

        # Dispatch real order
        else:
            try:
                res = self.sell_order(symbol=self.active_bot.pair, qty=qty, price=supress_notation(price, self.price_precision))
            except Exception as err:
                raise TraillingProfitError(err)

        order_data = BinanceOrderModel(
            timestamp=res["transactTime"],
            order_id=res["orderId"],
            deal_type="take_profit",
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res["price"],
            qty=res["origQty"],
            fills=res["fills"],
            time_in_force=res["timeInForce"],
            status=res["status"],
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
        print(msg)

        bot = self.save_bot_streaming()
        return bot

    def so_update_deal(self, so_index):
        """
        Executes when
        - Klines websocket triggers condition price = safety order price
        - Get qty and price (use trade books so it can sell immediately at limit)
        - Update deal.price, deal.qty
        - Cancel old take profit order to unlock balance
        - Create new so
        - Deactivate so
        - Update DB with new deal data
        - Create new take profit order
        - Update DB with new take profit deal data

        Not for use when opening new deal
        """
        pair = self.active_bot.pair
        so_qty = self.active_bot.safety_orders[so_index].so_size
        price = self.matching_engine(pair, True, so_qty)
        qty = round_numbers(
            float(so_qty),
            self.qty_precision,
        )
        order = {
            "pair": pair,
            "qty": supress_notation(qty, self.qty_precision),
            "price": supress_notation(price, self.price_precision),
        }

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(pair, price, qty, "BUY")
        else:
            try:
                res = self.bb_request(self.bb_buy_order_url, "POST", payload=order)
            except NotEnoughFunds as error:
                # If there are no funds to execute SO, this needs to be done manually then
                # Deactivate SO to avoid it triggering constantly
                # Send error message to the bot logs
                self.active_bot.safety_orders[so_index].status = 2
                self.active_bot.errors.append("Not enough funds to execute SO")

                bot = encode_json(self.active_bot)
                if "_id" in bot:
                    bot.pop("_id")

                self.db_collection.update_one(
                    {"id": self.active_bot.id},
                    {"$set": bot},
                )
                return

        safety_order = BinanceOrderModel(
            timestamp=res["transactTime"],
            order_type=res["type"],
            order_id=res["orderId"],
            pair=res["symbol"],
            deal_type=f"so_{so_index}",
            order_side=res["side"],
            price=res["price"],
            qty=res["origQty"],
            fills=res["fills"],
            status=res["status"],
            time_in_force=res["timeInForce"],
        )

        self.active_bot.orders.append(safety_order)
        self.active_bot.safety_orders[so_index].status = 1
        self.active_bot.safety_orders[so_index].order_id = res["orderId"]
        self.active_bot.safety_orders[so_index].buy_timestamp = res["transactTime"]
        self.active_bot.safety_orders[so_index].so_size = res[
            "origQty"
        ]  # update with actual quantity

        for chunk in safety_order.fills:
            self.active_bot.total_commission += float(chunk["commission"])

        if hasattr(self.active_bot.deal, "buy_total_qty"):
            buy_total_qty = float(self.active_bot.deal.buy_total_qty) + float(
                res["origQty"]
            )
        else:
            buy_total_qty = self.active_bot.base_order_size

        self.active_bot.deal.buy_total_qty = buy_total_qty

        # weighted average buy price
        # first store the previous price for the record
        self.active_bot.deal.original_buy_price = self.active_bot.deal.buy_price
        if self.active_bot.orders and len(self.active_bot.orders) > 0:
            weighted_avg_buy_price = 0
            for order in self.active_bot.orders:
                if order.deal_type == "base_order":
                    weighted_avg_buy_price += float(order.qty) * float(order.price)
                if order.deal_type.startswith("so"):
                    weighted_avg_buy_price += float(order.qty) * float(order.price)

        self.active_bot.deal.buy_price = weighted_avg_buy_price / buy_total_qty

        order_id = None
        for order in self.active_bot.orders:
            if order.deal_type == "take_profit":
                order_id = order.order_id
                self.active_bot.orders.remove(order)
                break

        if order_id and self.db_collection.name != "paper_trading":
            # First cancel old order to unlock balance
            try:
                self.bb_request(
                    f"{self.bb_close_order_url}/{self.active_bot.pair}/{order_id}",
                    "DELETE",
                )
                self.update_deal_logs("Old take profit order cancelled")
            except HTTPError as error:
                self.update_deal_logs(
                    f"Take profit order not found, no need to cancel, {error}"
                )

        # Because buy_price = avg_buy_price after so executed
        # we can use this to update take_profit_price
        new_tp_price = float(self.active_bot.deal.buy_price) * (
            1 + float(self.active_bot.take_profit) / 100
        )

        # Reset deal take_profit and trailling (even if there is no trailling, setting it 0 would be equal to cancelling)
        self.active_bot.deal.take_profit_price = new_tp_price
        self.active_bot.deal.trailling_stop_loss_price = 0

        try:
            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            self.db_collection.update_one(
                {"id": self.active_bot.id},
                {"$set": bot},
            )
            self.update_deal_logs("Safety order triggered!")
            print("Safety order triggered!")

        except ValidationError as error:
            self.update_deal_logs(f"Safety orders error: {error}")
            return
        except (TypeError, AttributeError) as error:
            message = str(";".join(error.args))
            self.update_deal_logs(f"Safety orders error: {message}")
            return
        except Exception as error:
            self.update_deal_logs(f"Safety orders error: {error}")
            return

        pass

    def streaming_updates(self, close_price, open_price):
        self.active_bot.deal.current_price = close_price
        self.save_bot_streaming()
        # Stop loss
        if (float(self.active_bot.stop_loss) > 0 and float(self.active_bot.deal.stop_loss_price) > float(close_price)):
            self.execute_stop_loss(close_price)
            if self.active_bot.margin_short_reversal:
                self.switch_margin_short(close_price)
                raise TerminateStreaming("Streaming update needs to restart for autoswitched bot")
            return

        # Take profit trailling
        if (self.active_bot.trailling == "true" or self.active_bot.trailling) and float(self.active_bot.deal.buy_price) > 0:
            # If current price didn't break take_profit (first time hitting take_profit or trailling_stop_loss lower than base_order buy_price)
            if self.active_bot.deal.trailling_stop_loss_price == 0:
                trailling_price = float(self.active_bot.deal.buy_price) * (
                    1 + (float(self.active_bot.take_profit) / 100)
                )
            else:
                # Current take profit + next take_profit
                trailling_price = float(self.active_bot.deal.trailling_stop_loss_price) * (
                    1 + (float(self.active_bot.take_profit) / 100)
                )

            self.active_bot.deal.trailling_profit_price = trailling_price
            # Direction 1 (upward): breaking the current trailling
            if float(close_price) >= float(trailling_price):
                new_take_profit = float(trailling_price) * (
                    1 + (float(self.active_bot.take_profit) / 100)
                )
                new_trailling_stop_loss = float(trailling_price) - (
                    float(trailling_price)
                    * (float(self.active_bot.trailling_deviation) / 100)
                )
                # Update deal take_profit
                self.active_bot.deal.take_profit_price = new_take_profit
                # take_profit but for trailling, to avoid confusion
                # trailling_profit_price always be > trailling_stop_loss_price
                self.active_bot.deal.trailling_profit_price = new_take_profit

                if new_trailling_stop_loss > self.active_bot.deal.buy_price:
                    # Selling below buy_price will cause a loss
                    # instead let it drop until it hits safety order or stop loss
                    logging.info(
                        f"{self.active_bot.pair} Updating take_profit_price, trailling_profit and trailling_stop_loss_price! {new_take_profit}"
                    )
                    # Update trailling_stop_loss
                    self.active_bot.deal.trailling_stop_loss_price = new_trailling_stop_loss
                    logging.info(
                        f'{datetime.utcnow()} Updated {self.active_bot.pair} trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}'
                    )
                else:
                    # Protect against drops by selling at buy price + 0.75% commission
                    self.active_bot.deal.trailling_stop_loss_price = (
                        float(self.active_bot.deal.buy_price) * 1.075
                    )
                    logging.info(
                        f'{datetime.utcnow()} Updated {self.active_bot.pair} trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}'
                    )

            self.save_bot_streaming()

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
                logging.info(
                    f'Hit trailling_stop_loss_price {self.active_bot.deal.trailling_stop_loss_price}. Selling {self.active_bot.pair}'
                )
                try:
                    self.trailling_profit()
                    # This terminates the bot
                    return

                except Exception as error:
                    logging.error(error)
                    return

        # Open safety orders
        # When bot = None, when bot doesn't exist (unclosed websocket)
        if hasattr(self.active_bot, "safety_orders") and len(self.active_bot.safety_orders) > 0:
            for key, so in enumerate(self.active_bot.safety_orders):
                # Index is the ID of the safety order price that matches safety_orders list
                if hasattr(self.active_bot, "status") and self.active_bot.status == 0 and so.buy_price >= float(close_price):
                    self.so_update_deal(key)

        # Execute dynamic_take_profit at the end,
        # so that trailling_take_profit and trailling_stop_loss can execute before
        # else trailling_stop_loss could be hit but then changed because of dynamic_tp
        if self.active_bot.trailling and self.active_bot.dynamic_trailling:
            # Returns bot, to keep modifying in subsequent checks
            bot = self.dynamic_take_profit(self.active_bot, close_price)