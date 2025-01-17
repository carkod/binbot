from typing import Type, Union
from database.models.bot_table import BotTable, PaperTradingTable
from bots.models import BotModel, OrderModel
from tools.enum_definitions import DealType, OrderSide, Status, Strategy
from tools.exceptions import TakeProfitError
from tools.handle_error import (
    handle_binance_errors,
)
from tools.round_numbers import round_numbers, supress_notation
from deals.base import BaseDeal
from deals.models import DealModel
from database.paper_trading_crud import PaperTradingTableCrud


class DealAbstract(BaseDeal):
    """
    Centralized deal controller.

    This is the first step that comes after a bot is saved
    1. Save bot
    2. Open deal (deal controller)
    3. Update deals (deal update controller)

    - db_collection = ["bots", "paper_trading"].
    paper_trading uses simulated orders and bot uses real binance orders.
    PaperTradingTable is implemented, PaperTradingController with the db operations is not.
    - bot: BotModel (at some point to refactor into BotTable as they are both pydantic models)
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ):
        super().__init__(bot, db_table)
        self.active_bot = bot
        self.db_table = db_table

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
            qty = self.compute_qty(self.active_bot.pair)

        qty = round_numbers(buy_total_qty, self.qty_precision)
        price = round_numbers(price, self.price_precision)

        if self.db_table == PaperTradingTable:
            res = self.simulate_order(self.active_bot.pair, OrderSide.sell)
        else:
            qty = round_numbers(qty, self.qty_precision)
            price = round_numbers(price, self.price_precision)
            res = self.sell_order(symbol=self.active_bot.pair, qty=qty)

        # If error pass it up to parent function, can't continue
        if "error" in res:
            raise TakeProfitError(res["error"])

        order_data = OrderModel(
            timestamp=res["transactTime"],
            order_id=res["orderId"],
            deal_type="take_profit",
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
        self.active_bot.deal.take_profit_price = float(res["price"])
        self.active_bot.deal.closing_price = float(res["price"])
        self.active_bot.deal.closing_qty =float(res["origQty"])
        self.active_bot.deal.closing_timestamp = float(res["transactTime"])
        self.active_bot.status = Status.completed

        bot = self.controller.save(self.active_bot)
        bot = BotModel.model_construct(**bot.model_dump())
        self.controller.update_logs("Completed take profit", self.active_bot)

        return bot

    def close_all(self) -> BotModel:
        """
        Close all deals and sell pair
        1. Close all deals
        2. Sell Coins
        3. Delete bot
        """
        orders = self.active_bot.orders

        # Close all active orders
        if len(orders) > 0:
            for d in orders:
                if d.status == "NEW" or d.status == "PARTIALLY_FILLED":
                    self.controller.update_logs(
                        "Failed to close all active orders (status NEW), retrying...",
                        self.active_bot,
                    )
                    self.replace_order(d.order_id)

        # Sell everything
        pair = self.active_bot.pair
        base_asset = self.find_baseAsset(pair)
        balance = self.get_single_raw_balance(base_asset)
        if balance > 0:
            qty = round_numbers(balance, self.qty_precision)
            price: float = float(self.matching_engine(pair, True, qty))
            price = round_numbers(price, self.price_precision)

            res = self.sell_order(symbol=self.active_bot.pair, qty=qty, price=price)

            order_data = OrderModel(
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

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.closing_price = res["price"]
        self.active_bot.deal.closing_qty = res["origQty"]
        self.active_bot.deal.closing_timestamp = res["transactTime"]

        self.controller.update_logs(
            "Panic sell triggered. All active orders closed", self.active_bot
        )
        self.active_bot.status = Status.completed
        self.controller.save(self.active_bot)

        return self.active_bot

    def update_take_profit(self, order_id: int) -> BotModel:
        """
        Update take profit after websocket order endpoint triggered
        - Close current opened take profit order
        - Create new take profit order
        - Update database by replacing old take profit deal with new take profit deal
        """
        bot = self.active_bot
        if bot.deal:
            find_base_order = next(
                (order.order_id == order_id for order in bot.orders), None
            )
            if find_base_order:
                so_deal_price = bot.deal.opening_price
                # Create new take profit order
                new_tp_price = float(so_deal_price) + (
                    float(so_deal_price) * float(bot.take_profit) / 100
                )
                asset = self.find_baseAsset(bot.pair)

                # First cancel old order to unlock balance
                self.delete_order(bot.pair, order_id)

                raw_balance = self.get_single_raw_balance(asset)
                qty = round_numbers(raw_balance, self.qty_precision)
                res = self.sell_order(
                    symbol=self.active_bot.pair,
                    qty=qty,
                    price=round_numbers(new_tp_price, self.price_precision),
                )

                # New take profit order successfully created
                order = handle_binance_errors(res)

                # Replace take_profit order
                take_profit_order = OrderModel(
                    timestamp=order["transactTime"],
                    order_id=order["orderId"],
                    deal_type=DealType.take_profit,
                    pair=order["symbol"],
                    order_side=order["side"],
                    order_type=order["type"],
                    price=order["price"],
                    qty=order["origQty"],
                    time_in_force=order["timeInForce"],
                    status=order["status"],
                )

                total_commission = self.calculate_total_commissions(res["fills"])
                # Build new deals list
                new_deals = []
                for d in bot.orders:
                    if d.deal_type != DealType.take_profit:
                        new_deals.append(d)

                # Append now new take_profit deal
                new_deals.append(take_profit_order)
                self.active_bot.orders = new_deals
                self.active_bot.total_commission = total_commission
                self.controller.save(self.active_bot)
                self.controller.update_logs("take_profit deal successfully updated")
                return self.active_bot
        else:
            self.controller.update_logs(
                "Error: Bot does not contain a base order deal", self.active_bot
            )
            raise ValueError("Bot does not contain a base order deal")
        return self.active_bot

    def open_deal_trailling_parameters(self):
        """
        Optional deals section

        The following functionality is triggered according to the options set in the bot
        it comes after SpotConcrete.open_deal or MarginConcrete.open_deal
        The reason why it's put here, it's because it's agnostic of what type of deal
        strategy, we always execute these
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

        # Margin short Take profit
        if (
            self.active_bot.take_profit > 0
            and self.active_bot.strategy == Strategy.margin_short
        ):
            if self.active_bot.take_profit:
                price = float(self.active_bot.deal.closing_price)
                take_profit_price = price - (
                    price * (self.active_bot.take_profit) / 100
                )
                self.active_bot.deal.take_profit_price = take_profit_price

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
        self.controller.save(self.active_bot)
        self.controller.update_logs("Bot activated", self.active_bot)
        return self.active_bot

    def base_order(self) -> BotModel:
        """
        Required initial order to trigger long strategy bot.
        Other orders require this to execute,
        therefore should fail if not successful

        1. Initial base purchase
        2. Set take_profit
        """

        # Long position does not need qty in take_profit
        # initial price with 1 qty should return first match
        price = float(
            self.matching_engine(
                self.active_bot.pair, True, qty=self.active_bot.base_order_size
            )
        )
        qty = round_numbers(
            (float(self.active_bot.base_order_size) / float(price)),
            self.qty_precision,
        )
        # setup stop_loss_price
        stop_loss_price: float = 0
        if float(self.active_bot.stop_loss) > 0:
            stop_loss_price = price - (price * (float(self.active_bot.stop_loss) / 100))

        if isinstance(self.controller, PaperTradingTableCrud):
            res = self.simulate_order(
                self.active_bot.pair,
                OrderSide.buy,
            )
        else:
            res = self.buy_order(
                symbol=self.active_bot.pair,
                qty=qty,
                price=supress_notation(price, self.price_precision),
            )

        order_data = OrderModel(
            timestamp=res["transactTime"],
            order_id=res["orderId"],
            deal_type=DealType.base_order,
            pair=res["symbol"],
            order_side=res["side"],
            order_type=res["type"],
            price=res["price"],
            qty=res["origQty"],
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.orders.append(order_data)
        tp_price = float(res["price"]) * 1 + (float(self.active_bot.take_profit) / 100)

        self.active_bot.deal = DealModel(
            opening_timestamp=float(res["transactTime"]),
            opening_price=float(res["price"]),
            opening_qty=float(res["origQty"]),
            current_price=float(res["price"]),
            take_profit_price=tp_price,
            stop_loss_price=stop_loss_price,
        )

        # temporary measures to keep deal up to date
        # once bugs are fixed, this can be removed to improve efficiency
        self.active_bot.status = Status.active
        self.controller.save(self.active_bot)

        # Only signal for the whole activation
        self.base_producer.update_required(self.producer, "EXECUTE_SPOT_OPEN_DEAL")
        return self.active_bot
