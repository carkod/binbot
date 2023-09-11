import requests

from bots.schemas import BotSchema
from deals.base import BaseDeal
from deals.margin import MarginDeal
from deals.models import BinanceOrderModel
from deals.schema import DealSchema, OrderSchema
from pymongo import ReturnDocument
from tools.enum_definitions import Status
from tools.exceptions import (
    ShortStrategyError,
    TakeProfitError,
)
from tools.handle_error import (
    encode_json,
    handle_binance_errors,
)
from tools.round_numbers import round_numbers, supress_notation


class CreateDealControllerError(Exception):
    pass


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

    def __init__(self, bot, db_collection="paper_trading"):
        # Inherit from parent class
        super().__init__(bot, db_collection)
        self.active_bot = BotSchema.parse_obj(bot)

    def get_one_balance(self, symbol="BTC"):
        # Response after request
        data = self.bb_request(url=self.bb_balance_url)
        symbol_balance = next(
            (x["free"] for x in data["data"] if x["asset"] == symbol), None
        )
        return symbol_balance

    def compute_qty(self, pair):
        """
        Helper function to compute buy_price.
        Previous qty = bot.deal["buy_total_qty"]
        """

        asset = self.find_baseAsset(pair)
        balance = self.get_one_balance(asset)
        if not balance:
            return None
        qty = round_numbers(balance, self.qty_precision)
        return qty

    def base_order(self):
        """
        Required initial order to trigger bot.
        Other orders require this to execute,
        therefore should fail if not successful

        1. Initial base purchase
        2. Set take_profit
        """

        pair = self.active_bot.pair

        # Long position does not need qty in take_profit
        # initial price with 1 qty should return first match
        price = float(self.matching_engine(pair, True))
        qty = round_numbers(
            (float(self.active_bot.base_order_size) / float(price)),
            self.qty_precision,
        )
        # setup stop_loss_price
        stop_loss_price = 0
        if float(self.active_bot.stop_loss) > 0:
            stop_loss_price = price - (price * (float(self.active_bot.stop_loss) / 100))

        if self.db_collection.name == "paper_trading":
            res = self.simulate_order(
                pair, supress_notation(price, self.price_precision), qty, "BUY"
            )
        else:
            res = self.buy_order(symbol=pair, qty=qty, price=supress_notation(price, self.price_precision))

        order_data = OrderSchema(
            timestamp=res["transactTime"],
            order_id=res["orderId"],
            deal_type="base_order",
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
        tp_price = float(res["price"]) * 1 + (float(self.active_bot.take_profit) / 100)

        self.active_bot.deal = DealSchema(
            buy_timestamp=res["transactTime"],
            buy_price=res["price"],
            buy_total_qty=res["origQty"],
            current_price=res["price"],
            take_profit_price=tp_price,
            stop_loss_price=stop_loss_price,
        )

        # Activate bot
        self.active_bot.status = Status.active

        bot = encode_json(self.active_bot)
        if "_id" in bot:
            bot.pop("_id")  # _id is what causes conflict not id

        document = self.db_collection.find_one_and_update(
            {"id": self.active_bot.id},
            {"$set": bot},
            return_document=ReturnDocument.AFTER,
        )

        return document

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
            res = self.simulate_order(self.active_bot.pair, price, qty, "SELL")
            if price:
                res = self.simulate_order(
                    self.active_bot.pair,
                    price,
                    qty,
                    "SELL",
                )
            else:
                price = (1 + (float(self.active_bot.take_profit) / 100)) * float(
                    deal_buy_price
                )
                res = self.simulate_order(
                    self.active_bot.pair,
                    price,
                    qty,
                    "SELL",
                )
        else:
            qty = supress_notation(qty, self.qty_precision)
            price = supress_notation(price, self.price_precision)
            res = self.sell_order(symbol=self.active_bot.pair, qty=qty, price=price)

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
            fills=res["fills"],
            time_in_force=res["timeInForce"],
            status=res["status"],
        )

        self.active_bot.orders.append(order_data)
        self.active_bot.deal.take_profit_price = res["price"]
        self.active_bot.deal.sell_price = res["price"]
        self.active_bot.deal.sell_qty = res["origQty"]
        self.active_bot.deal.sell_timestamp = res["transactTime"]
        self.active_bot.status = Status.completed
        msg = f"Completed take profit"
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

    def close_all(self):
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
                if "deal_type" in d and (
                    d["status"] == "NEW" or d["status"] == "PARTIALLY_FILLED"
                ):
                    self.update_deal_logs(
                        "Failed to close all active orders (status NEW), retrying..."
                    )
                    res = self.replace_order(d["orderId"])

        # Sell everything
        pair = self.active_bot.pair
        base_asset = self.find_baseAsset(pair)
        balance = self.get_one_balance(base_asset)
        if balance:
            qty = round_numbers(balance, self.qty_precision)
            price = float(self.matching_engine(pair, True, qty))
            price = supress_notation(price, self.price_precision)
            self.sell_order(symbol=self.active_bot.pair, qty=qty, price=price)

        return

    def update_take_profit(self, order_id):
        """
        Update take profit after websocket order endpoint triggered
        - Close current opened take profit order
        - Create new take profit order
        - Update database by replacing old take profit deal with new take profit deal
        """
        bot = self.active_bot
        if "deal" in bot:
            if bot.deal["order_id"] == order_id:
                so_deal_price = bot.deal["buy_price"]
                # Create new take profit order
                new_tp_price = float(so_deal_price) + (
                    float(so_deal_price) * float(bot.take_profit) / 100
                )
                asset = self.find_baseAsset(bot.pair)

                # First cancel old order to unlock balance
                close_order_params = {"symbol": bot.pair, "orderId": order_id}
                cancel_response = requests.post(
                    url=self.bb_close_order_url, params=close_order_params
                )
                if cancel_response.status_code != 200:
                    print("Take profit order not found, no need to cancel")
                else:
                    print("Old take profit order cancelled")

                qty = round_numbers(self.get_one_balance(asset), self.qty_precision)
                res = self.sell_order(symbol=self.active_bot.pair, qty=qty, price=supress_notation(new_tp_price, self.price_precision))

                # New take profit order successfully created
                order = handle_binance_errors(res)

                # Replace take_profit order
                take_profit_order = {
                    "deal_type": "take_profit",
                    "order_id": order["orderId"],
                    "pair": order["symbol"],
                    "order_side": order["side"],
                    "order_type": order["type"],
                    "price": order["price"],
                    "qty": order["origQty"],
                    "fills": order["fills"],
                    "time_in_force": order["timeInForce"],
                    "status": order["status"],
                }
                # Build new deals list
                new_deals = []
                for d in bot.deals:
                    if d["deal_type"] != "take_profit":
                        new_deals.append(d)

                # Append now new take_profit deal
                new_deals.append(take_profit_order)
                self.active_bot.orders = new_deals
                self.db.bots.update_one(
                    {"id": self.active_bot.id},
                    {
                        "$push": {
                            "orders": take_profit_order,
                            "errors": "take_profit deal successfully updated",
                        }
                    },
                )
                return
        else:
            self.update_deal_logs("Error: Bot does not contain a base order deal")


    def open_deal(self):
        """
        Mandatory deals section

        - If base order deal is not executed, bot is not activated
        """
        # Short strategy checks
        if self.active_bot.strategy == "short":
            if (
                not hasattr(self.active_bot, "short_buy_price")
                or float(self.active_bot.short_buy_price) == 0
            ):
                raise ShortStrategyError(
                    "Short strategy requires short_buy_price to be set, or it will never trigger"
                )
            else:
                pass

        # If there is already a base order do not execute
        base_order_deal = next(
            (
                bo_deal
                for bo_deal in self.active_bot.orders
                if bo_deal.deal_type == "base_order"
            ),
            None,
        )

        if not base_order_deal:
            if self.active_bot.strategy == "margin_short":
                self.active_bot = MarginDeal(
                    bot=self.active_bot, db_collection_name=self.db_collection.name
                ).margin_short_base_order()
            else:
                bot = self.base_order()
                self.active_bot = BotSchema.parse_obj(bot)

        """
        Optional deals section

        The following functionality is triggered according to the options set in the bot
        """

        # Update stop loss regarless of base order
        if (
            hasattr(self.active_bot, "stop_loss")
            and float(self.active_bot.stop_loss) > 0
        ):
            if self.active_bot.strategy == "margin_short":
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
            hasattr(self.active_bot, "take_profit")
            and float(self.active_bot.take_profit) > 0
            and self.active_bot.strategy == "margin_short"
        ):
            self.active_bot = MarginDeal(
                bot=self.active_bot, db_collection_name=self.db_collection.name
            ).set_margin_take_profit()

        # Keep trailling_stop_loss_price up to date in case of failure to update in autotrade
        # if we don't do this, the trailling stop loss will trigger
        if (
            self.active_bot.deal
            and (
                self.active_bot.deal.trailling_stop_loss_price > 0
                or self.active_bot.deal.trailling_stop_loss_price
                < self.active_bot.deal.buy_price
            )
        ):
            take_profit_price = float(self.active_bot.deal.buy_price) * (
                1 + (float(self.active_bot.take_profit) / 100)
            )
            self.active_bot.deal.take_profit_price = take_profit_price
            # Update trailling_stop_loss
            # an update of the
            self.active_bot.deal.trailling_stop_loss_price = 0

        self.active_bot.status = Status.active
        bot = encode_json(self.active_bot)
        if "_id" in bot:
            bot.pop("_id")

        self.db_collection.update_one({"id": self.active_bot.id}, {"$set": bot})
        return
