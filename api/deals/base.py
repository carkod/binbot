import uuid
import requests
import numpy
import logging

from decimal import Decimal
from time import time

from orders.controller import OrderController
from bots.schemas import BotSchema
from db import setup_db
from tools.handle_error import encode_json
from pymongo import ReturnDocument
from tools.round_numbers import round_numbers
from tools.handle_error import handle_binance_errors
from scipy.stats import linregress


class DealCreationError(Exception):
    pass

class StreamingSaveError(Exception):
    pass

class BaseDeal(OrderController):
    """
    Base Deal class to share with CreateDealController and MarginDeal
    """

    def __init__(self, bot, db_collection_name):
        self.active_bot = BotSchema.parse_obj(bot)
        super().__init__()
        self.db_collection = self.db[db_collection_name]

    def __repr__(self) -> str:
        """
        To check that BaseDeal works for all children classes
        """
        return f"BaseDeal({self.__dict__})"

    def generate_id(self):
        return uuid.uuid4().hex

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

    def simulate_order(self, pair, price, qty, side):
        order = {
            "symbol": pair,
            "orderId": self.generate_id(),
            "orderListId": -1,
            "clientOrderId": self.generate_id(),
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": [],
        }
        return order

    def simulate_response_order(self, pair, price, qty, side):
        response_order = {
            "symbol": pair,
            "orderId": id,
            "orderListId": -1,
            "clientOrderId": id,
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": [],
        }
        return response_order

    def update_deal_logs(self, msg):
        self.db_collection.update_one(
            {"id": self.active_bot.id},
            {"$push": {"errors": msg}},
        )
        return msg

    def replace_order(self, cancel_order_id):
        payload = [
            ("symbol", self.active_bot.pair),
            ("quantity", self.active_bot.base_order_size),
            ("cancelOrderId", cancel_order_id),
            ("type", "MARKET"),
            ("side", "SELL"),
            ("cancelReplaceMode", "ALLOW_FAILURE"),
        ]
        response = self.signed_request(
            url=self.cancel_replace_url, method="POST", payload=payload
        )
        if "code" in response:
            raise DealCreationError(response["msg"], response["data"])

        return response["newOrderResponse"]

    def close_open_orders(self, symbol):
        """
        Check open orders and replace with new
        """
        open_orders = self.signed_request(self.open_orders, payload={"symbol": symbol})
        for order in open_orders:
            if order["status"] == "NEW":
                self.signed_request(self.order_url, method="DELETE", payload={"symbol": symbol, "orderId": order["orderId"]})
                return True
        return False

    def update_required(self):
        """
        Terminate streaming and restart list of bots required

        This will queue up a timer to restart streaming_controller when timer is reached
        This timer is added, so that update_required petitions can be accumulated and
        avoid successively restarting streaming_controller, which consumes a lot of memory

        This means that everytime there is an update in the list of active bots,
        it will reset the timer
        """
        self.db.research_controller.update_one(
            {"_id": "settings"}, {"$set": {"update_required": time()}}
        )
        return

    def save_bot_streaming(self):
        """
        MongoDB query to save bot using Pydantic

        This function differs from usual save query in that
        it returns the saved bot, thus called streaming, it's
        specifically for streaming saves
        """

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
            self.update_deal_logs(f"Failed to save bot during streaming updates: {error}")
            raise StreamingSaveError(error)

        return bot

    def dynamic_take_profit(self, current_bot, close_price):

        self.active_bot = BotSchema.parse_obj(current_bot)

        params = {
            "symbol": self.active_bot.pair,
            "interval": self.active_bot.candlestick_interval,
        }
        res = requests.get(url=self.bb_candlestick_url, params=params)
        data = handle_binance_errors(res)
        list_prices = numpy.array(data["trace"][0]["close"]).astype(numpy.single)
        series_sd = numpy.std(list_prices.astype(numpy.single))
        sd = series_sd / float(close_price)
        dates = numpy.array(data["trace"][0]["x"])

        # Calculate linear regression to get trend
        slope, intercept, rvalue, pvalue, stderr = linregress(dates, list_prices)

        if sd >= 0:
            logging.debug(
                f"dynamic profit for {self.active_bot.pair} sd: {sd}",
                f'slope is {"positive" if slope > 0 else "negative"}',
            )
            if (
                self.active_bot.deal.trailling_stop_loss_price > 0
                and self.active_bot.deal.trailling_stop_loss_price
                > self.active_bot.deal.base_order_price
                and float(close_price)
                > self.active_bot.deal.trailling_stop_loss_price
                and (
                    (self.active_bot.strategy == "long" and slope > 0)
                    or (self.active_bot.strategy == "margin_short" and slope < 0)
                )
                and self.active_bot.deal.sd > sd
            ):
                # Only do dynamic trailling if regression line confirms it
                volatility: float = float(sd) / float(close_price)
                if volatility < 0.018:
                    volatility = 0.018
                elif volatility > 0.088:
                    volatility = 0.088

                # sd is multiplied by 2 to increase the difference between take_profit and trailling_stop_loss
                # this avoids closing too early
                new_trailling_stop_loss_price = float(close_price) - (
                    float(close_price) * volatility
                )
                # deal.sd comparison will prevent it from making trailling_stop_loss too big
                # and thus losing all the gains
                if new_trailling_stop_loss_price > float(
                    self.active_bot.deal.buy_price
                ) and sd < self.active_bot.deal.sd:
                    self.active_bot.trailling_deviation = volatility * 100
                    self.active_bot.deal.trailling_stop_loss_price = float(
                        close_price
                    ) - (float(close_price) * volatility)
                    # Update tralling_profit price
                    logging.info(
                        f"Updated trailling_deviation and take_profit {self.active_bot.deal.trailling_stop_loss_price}"
                    )
                    self.active_bot.deal.take_profit_price = float(close_price) + (
                        float(close_price) * volatility
                    )
                    self.active_bot.deal.trailling_profit_price = float(close_price) + (
                        float(close_price) * volatility
                    )

        self.active_bot.deal.sd = sd
        bot = self.save_bot_streaming()
        return bot
