from orders.controller import OrderController
from bots.schemas import BotSchema
from deals.base import BaseDeal
from deals.margin import MarginDeal
from deals.models import BinanceOrderModel
from pymongo import ReturnDocument
from tools.enum_definitions import DealType, Status, Strategy
from tools.exceptions import TakeProfitError
from tools.handle_error import (
    encode_json,
    handle_binance_errors,
)
from tools.round_numbers import round_numbers, supress_notation


class CreateDealController(BaseDeal):
    """
    Centralized deal controller.

    This is the first step that comes after a bot is saved
    1. Save bot
    2. Open deal (deal controller)
    3. Update deals (deal update controller)

    - db_collection = ["bots", "paper_trading"].
    paper_trading uses simulated orders and bot uses real binance orders
    """

    def __init__(self, bot: BotSchema, db_collection="paper_trading"):
        # Inherit from parent class
        super().__init__(bot, db_collection)
        self.active_bot = bot

    def compute_qty(self, pair):
        """
        Helper function to compute buy_price.
        Previous qty = bot.deal["buy_total_qty"]
        """

        asset = self.find_baseAsset(pair)
        balance = self.get_raw_balance(asset)
        if not balance:
            return None
        qty = round_numbers(balance, self.qty_precision)
        return qty

    def take_profit_order(self) -> BotSchema:
        """
        take profit order (Binance take_profit)
        - We only have stop_price, because there are no book bids/asks in t0
        - take_profit order can ONLY be executed once base order is filled (on Binance)
        """

        deal_buy_price = self.active_bot.deal.buy_price
        buy_total_qty = self.active_bot.deal.buy_total_qty
        price = (1 + (float(self.active_bot.take_profit) / 100)) * float(deal_buy_price)

        if self.db_collection.name == "paper_trading":
            qty = self.active_bot.deal.buy_total_qty
        else:
            qty = self.compute_qty(self.active_bot.pair)

        qty = supress_notation(buy_total_qty, self.qty_precision)
        price = supress_notation(price, self.price_precision)

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(self.active_bot.pair, qty, "SELL")
            if price:
                res = self.simulate_order(
                    self.active_bot.pair,
                    qty,
                    "SELL",
                )
            else:
                price = (1 + (float(self.active_bot.take_profit) / 100)) * float(
                    deal_buy_price
                )
                res = self.simulate_order(
                    self.active_bot.pair,
                    qty,
                    "SELL",
                )
        else:
            qty = supress_notation(qty, self.qty_precision)
            price = supress_notation(price, self.price_precision)
            res = self.sell_order(symbol=self.active_bot.pair, qty=qty)

        # If error pass it up to parent function, can't continue
        if "error" in res:
            raise TakeProfitError(res["error"])

        order_data = BinanceOrderModel(
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
        self.active_bot.deal.take_profit_price = res["price"]
        self.active_bot.deal.sell_price = res["price"]
        self.active_bot.deal.sell_qty = res["origQty"]
        self.active_bot.deal.sell_timestamp = res["transactTime"]
        self.active_bot.status = Status.completed
        msg = "Completed take profit"
        self.active_bot.errors.append(msg)

        try:
            bot = encode_json(self.active_bot)
            if "_id" in bot:
                bot.pop("_id")

            bot = self.db_collection.find_one_and_update(
                {"id": self.active_bot.id},
                {
                    "$set": bot,
                },
                return_document=ReturnDocument.AFTER,
            )
        except Exception as error:
            raise TakeProfitError(error)

        return bot

    def close_all(self) -> None:
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
                    self.update_deal_logs(
                        "Failed to close all active orders (status NEW), retrying...",
                        self.active_bot,
                    )
                    self.replace_order(d["orderId"])

        # Sell everything
        pair = self.active_bot.pair
        base_asset = self.find_baseAsset(pair)
        balance = self.get_raw_balance(base_asset)
        if balance:
            qty = round_numbers(balance[0], self.qty_precision)
            price: float = float(self.matching_engine(pair, True, qty))
            price = supress_notation(price, self.price_precision)
            self.sell_order(symbol=self.active_bot.pair, qty=qty, price=price)

        return

    def update_take_profit(self, order_id) -> None:
        """
        Update take profit after websocket order endpoint triggered
        - Close current opened take profit order
        - Create new take profit order
        - Update database by replacing old take profit deal with new take profit deal
        """
        bot = self.active_bot
        if "deal" in bot:
            find_base_order = next(bot.orders.order_id == order_id, None)
            if find_base_order:
                so_deal_price = bot.deal.buy_price
                # Create new take profit order
                new_tp_price = float(so_deal_price) + (
                    float(so_deal_price) * float(bot.take_profit) / 100
                )
                asset = self.find_baseAsset(bot.pair)

                # First cancel old order to unlock balance
                OrderController().delete_order(bot.pair, order_id)

                qty = round_numbers(self.get_raw_balance(asset), self.qty_precision)
                res = self.sell_order(
                    symbol=self.active_bot.pair,
                    qty=qty,
                    price=supress_notation(new_tp_price, self.price_precision),
                )

                # New take profit order successfully created
                order = handle_binance_errors(res)

                # Replace take_profit order
                take_profit_order = BinanceOrderModel(
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
                self.active_bot.errors.append("take_profit deal successfully updated")
                self.db.bots.update_one(
                    {"id": self.active_bot.id},
                    {"$set": self.active_bot.model_dump()},
                )
                return
        else:
            self.update_deal_logs(
                "Error: Bot does not contain a base order deal", self.active_bot
            )

    def open_deal(self) -> None:
        """
        Mandatory deals section

        - If base order deal is not executed, bot is not activated
        """

        # If there is already a base order do not execute
        base_order_deal = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == DealType.base_order
            ),
            None,
        )

        if not base_order_deal:
            if self.active_bot.strategy == Strategy.margin_short:
                self.active_bot = MarginDeal(
                    bot=self.active_bot, db_collection_name=self.db_collection.name
                ).margin_short_base_order()
            else:
                bot = self.base_order()
                self.active_bot = BotSchema(**bot)

        """
        Optional deals section

        The following functionality is triggered according to the options set in the bot
        """

        # Update stop loss regarless of base order
        if float(self.active_bot.stop_loss) > 0:
            if self.active_bot.strategy == Strategy.margin_short:
                self.active_bot = MarginDeal(
                    bot=self.active_bot, db_collection_name=self.db_collection.name
                ).set_margin_short_stop_loss()
            else:
                buy_price = float(self.active_bot.deal.buy_price)
                stop_loss_price = buy_price - (
                    buy_price * float(self.active_bot.stop_loss) / 100
                )
                self.active_bot.deal.stop_loss_price = supress_notation(
                    stop_loss_price, self.price_precision
                )

        # Margin short Take profit
        if (
            float(self.active_bot.take_profit) > 0
            and self.active_bot.strategy == Strategy.margin_short
        ):
            self.active_bot = MarginDeal(
                bot=self.active_bot, db_collection_name=self.db_collection.name
            ).set_margin_take_profit()

        # Keep trailling_stop_loss_price up to date in case of failure to update in autotrade
        # if we don't do this, the trailling stop loss will trigger
        if self.active_bot.deal and (
            self.active_bot.deal.trailling_stop_loss_price > 0
            or self.active_bot.deal.trailling_stop_loss_price
            < self.active_bot.deal.buy_price
        ):
            take_profit_price = float(self.active_bot.deal.buy_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price
            # Update trailling_stop_loss
            self.active_bot.deal.trailling_stop_loss_price = 0

        self.active_bot.status = Status.active
        bot = self.active_bot.model_dump()
        if "_id" in bot:
            bot.pop("_id")

        self.db_collection.update_one({"id": self.active_bot.id}, {"$set": bot})
        return
