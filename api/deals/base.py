import uuid
import requests
import numpy
import logging

from time import time

from orders.controller import OrderController
from bots.schemas import BotSchema
from pymongo import ReturnDocument
from tools.round_numbers import round_numbers, supress_notation
from tools.handle_error import handle_binance_errors, encode_json
from tools.exceptions import BinanceErrors
from scipy.stats import linregress
from tools.round_numbers import round_numbers_ceiling


# To be removed one day when commission endpoint found that provides this value
ESTIMATED_COMMISSIONS_RATE = 0.0075

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
        self.isolated_balance = None
        self.qty_precision = None
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

    def compute_margin_buy_back(
        self, pair: str, qty_precision
    ):
        """
        Same as compute_qty but with isolated margin balance

        Find available amount to buy_back
        this is the borrowed amount + interests.
        Decimals have to be rounded up to avoid leaving
        "leftover" interests
        """
        if not self.isolated_balance:
            self.isolated_balance = self.get_isolated_balance(pair)

        if (
            self.isolated_balance[0]["quoteAsset"]["free"] == 0
            or self.isolated_balance[0]["baseAsset"]["borrowed"] == 0
        ):
            return None

        qty = float(self.isolated_balance[0]["baseAsset"]["borrowed"]) + float(self.isolated_balance[0]["baseAsset"]["interest"]) + float(self.isolated_balance[0]["baseAsset"]["borrowed"]) * ESTIMATED_COMMISSIONS_RATE

        # Save API calls
        self.qty_precision = qty_precision

        if not self.qty_precision:
            self.qty_precision = self.get_qty_precision(pair)

        qty = round_numbers_ceiling(qty, self.qty_precision)
        free = float(self.isolated_balance[0]["baseAsset"]["free"])

        return qty, free

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
                volatility = float(sd) / float(close_price)
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

    def margin_liquidation(self, pair: str, qty_precision=None):
        """
        Emulate Binance Dashboard
        One click liquidation function
        """
        isolated_balance = self.get_isolated_balance(pair)
        base = isolated_balance[0]["baseAsset"]["asset"]
        quote = isolated_balance[0]["quoteAsset"]["asset"]
        # Check margin account balance first
        balance = float(isolated_balance[0]["quoteAsset"]["free"])
        borrowed_amount = float(isolated_balance[0]["baseAsset"]["borrowed"])
        free = float(isolated_balance[0]["baseAsset"]["free"])
        buy_margin_response = None
        qty_precision = self.get_qty_precision(pair)

        if borrowed_amount > 0:
            # repay_amount contains total borrowed_amount + interests + commissions for buying back
            # borrow amount is only the loan
            repay_amount, free = self.compute_margin_buy_back(pair, qty_precision)
            repay_amount = round_numbers_ceiling(repay_amount, qty_precision)

            if free == 0 or free < repay_amount:
                try:
                    # lot_size_by_symbol = self.lot_size_by_symbol(pair, "stepSize")
                    qty = round_numbers_ceiling(repay_amount - free, qty_precision)
                    buy_margin_response = self.buy_margin_order(
                        symbol=pair,
                        qty=qty,
                    )
                    repay_amount, free = self.compute_margin_buy_back(pair, qty_precision)
                except BinanceErrors as error:
                    if error.code == -3041:
                        # Not enough funds in isolated pair
                        # transfer from wallet
                        transfer_diff_qty = round_numbers_ceiling(repay_amount - free)
                        available_balance = self.get_one_balance(quote)
                        amount_to_transfer = 15 # Min amount
                        if available_balance < 15:
                            amount_to_transfer = available_balance
                        self.transfer_spot_to_isolated_margin(
                            asset=quote,
                            symbol=pair,
                            amount=amount_to_transfer,
                        )
                        buy_margin_response = self.buy_margin_order(pair, supress_notation(transfer_diff_qty, qty_precision))
                        repay_amount, free = self.compute_margin_buy_back(pair, qty_precision)
                        pass
                    if error.code == -2010:
                        # There is already money in the base asset
                        qty = round_numbers_ceiling(repay_amount - free, qty_precision)
                        price = float(self.matching_engine(pair, True, qty))
                        usdt_notional = price * qty
                        if usdt_notional < 15:
                            qty = round_numbers_ceiling(15 / price)

                        buy_margin_response = self.buy_margin_order(pair, supress_notation(qty, qty_precision))
                        repay_amount, free = self.compute_margin_buy_back(pair, qty_precision)
                        pass

            self.repay_margin_loan(
                asset=base,
                symbol=pair,
                amount=repay_amount,
                isIsolated="TRUE",
            )

            # get new balance
            isolated_balance = self.get_isolated_balance(pair)

        if float(isolated_balance[0]["quoteAsset"]["free"]) != 0:
            # transfer back to SPOT account
            self.transfer_isolated_margin_to_spot(
                asset=quote,
                symbol=pair,
                amount=isolated_balance[0]["quoteAsset"]["free"],
            )
        if float(isolated_balance[0]["baseAsset"]["free"]) != 0:
            self.transfer_isolated_margin_to_spot(
                asset=base,
                symbol=pair,
                amount=isolated_balance[0]["baseAsset"]["free"],
            )
                
        self.disable_isolated_margin_account(symbol=pair)
        return buy_margin_response

