import uuid
from time import time
from pymongo import ReturnDocument
from datetime import datetime
from deals.models import BinanceOrderModel, DealModel
from orders.controller import OrderController
from bots.schemas import BotSchema
from tools.round_numbers import round_numbers, supress_notation, round_numbers_ceiling
from tools.handle_error import encode_json
from tools.exceptions import BinanceErrors, DealCreationError, MarginLoanNotFound
from tools.enum_definitions import DealType, Status, Strategy


# To be removed one day en commission endpoint found that provides this value
ESTIMATED_COMMISSIONS_RATE = 0.0075


class BaseDeal(OrderController):
    """
    Base Deal class to share with CreateDealController and MarginDeal
    """

    def __init__(self, bot, db_collection_name):
        if not isinstance(bot, BotSchema):
            self.active_bot = BotSchema(**bot)
        else:
            self.active_bot = bot
        self.symbol = self.active_bot.pair
        super().__init__(symbol=self.active_bot.pair)
        self.db_collection = self._db[db_collection_name]
        self.market_domination_reversal = None
        if self.active_bot.strategy == Strategy.margin_short:
            self.isolated_balance: float = self.get_isolated_balance(self.symbol)

    def __repr__(self) -> str:
        """
        To check that BaseDeal works for all children classes
        """
        return f"BaseDeal({self.__dict__})"

    def generate_id(self):
        return uuid.uuid4()

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

    def compute_margin_buy_back(self):
        """
        Same as compute_qty but with isolated margin balance

        Find available amount to buy_back
        this is the borrowed amount + interests.
        Decimals have to be rounded up to avoid leaving
        "leftover" interests
        """
        if (
            self.isolated_balance[0]["quoteAsset"]["free"] == 0
            or self.isolated_balance[0]["baseAsset"]["borrowed"] == 0
        ):
            return None

        qty = (
            float(self.isolated_balance[0]["baseAsset"]["borrowed"])
            + float(self.isolated_balance[0]["baseAsset"]["interest"])
            + float(self.isolated_balance[0]["baseAsset"]["borrowed"])
            * ESTIMATED_COMMISSIONS_RATE
        )

        qty = round_numbers_ceiling(qty, self.qty_precision)
        free = float(self.isolated_balance[0]["baseAsset"]["free"])

        return qty, free

    def simulate_order(self, pair, price, qty, side):
        order = {
            "symbol": pair,
            "orderId": self.generate_id().int,
            "orderListId": -1,
            "clientOrderId": self.generate_id().hex,
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
            "orderId": self.generate_id().int,
            "orderListId": -1,
            "clientOrderId": self.generate_id().hex,
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
        open_orders = self.query_open_orders(symbol)
        for order in open_orders:
            if order["status"] == "NEW":
                self.signed_request(
                    self.order_url,
                    method="DELETE",
                    payload={"symbol": symbol, "orderId": order["orderId"]},
                )
                for order in self.active_bot.orders:
                    if order.order_id == order["orderId"]:
                        self.active_bot.orders.remove(self.active_bot.orders)
                        self.active_bot.errors.append("base_order not executed, therefore cancelled")
                        self.active_bot.status = Status.error
                        break

                return True
        return False

    def verify_deal_close_order(self):
        """
        Check if deal is closed by checking
        if there are any SELL orders
        """
        all_orders = self.get_all_orders(self.active_bot.pair, int(self.active_bot.deal.buy_timestamp))
        for order in all_orders:
            if order["side"] == "SELL" and order["price"] == self.active_bot.deal.take_profit_price and order["origQty"] == self.active_bot.deal.buy_total_qty:
                return order

        return None

    def base_order(self):
        """
        Required initial order to trigger long strategy bot.
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
            res = self.buy_order(
                symbol=pair,
                qty=qty,
                price=supress_notation(price, self.price_precision),
            )

        order_data = BinanceOrderModel(
            timestamp=res["transactTime"],
            order_id=res["orderId"],
            deal_type=DealType.base_order,
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

        self.active_bot.deal = DealModel(
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

    def margin_liquidation(self, pair: str, qty_precision=None):
        """
        Emulate Binance Dashboard One click liquidation function

        Args:
        - pair: a.k.a symbol, quote asset + base asset
        - qty_precision: to round numbers for Binance API. Passed optionally to
        reduce number of requests to avoid rate limit.
        """
        self.isolated_balance = self.get_isolated_balance(pair)
        base = self.isolated_balance[0]["baseAsset"]["asset"]
        quote = self.isolated_balance[0]["quoteAsset"]["asset"]
        # Check margin account balance first
        borrowed_amount = float(self.isolated_balance[0]["baseAsset"]["borrowed"])
        free = float(self.isolated_balance[0]["baseAsset"]["free"])
        buy_margin_response = None

        if borrowed_amount > 0:
            # repay_amount contains total borrowed_amount + interests + commissions for buying back
            # borrow amount is only the loan
            repay_amount, free = self.compute_margin_buy_back()
            repay_amount = round_numbers_ceiling(repay_amount, qty_precision)

            if free == 0 or free < repay_amount:
                try:
                    # lot_size_by_symbol = self.lot_size_by_symbol(pair, "stepSize")
                    qty = round_numbers_ceiling(repay_amount - free, qty_precision)
                    buy_margin_response = self.buy_margin_order(
                        symbol=pair,
                        qty=qty,
                    )
                    repay_amount, free = self.compute_margin_buy_back()
                except BinanceErrors as error:
                    if error.code == -3041:
                        # Not enough funds in isolated pair
                        # transfer from wallet
                        transfer_diff_qty = round_numbers_ceiling(repay_amount - free)
                        available_balance = self.get_one_balance(quote)
                        amount_to_transfer = 15  # Min amount
                        if available_balance < 15:
                            amount_to_transfer = available_balance
                        self.transfer_spot_to_isolated_margin(
                            asset=quote,
                            symbol=pair,
                            amount=amount_to_transfer,
                        )
                        buy_margin_response = self.buy_margin_order(
                            pair, supress_notation(transfer_diff_qty, qty_precision)
                        )
                        repay_amount, free = self.compute_margin_buy_back()
                        pass
                    if error.code == -2010 or error.code == -1013:
                        # There is already money in the base asset
                        qty = round_numbers_ceiling(repay_amount - free, qty_precision)
                        price = float(self.matching_engine(pair, True, qty))
                        usdt_notional = price * qty
                        if usdt_notional < 15:
                            qty = round_numbers_ceiling(15 / price)

                        buy_margin_response = self.buy_margin_order(
                            pair, supress_notation(qty, qty_precision)
                        )
                        repay_amount, free = self.compute_margin_buy_back()
                        pass

            self.repay_margin_loan(
                asset=base,
                symbol=pair,
                amount=repay_amount,
                isIsolated="TRUE",
            )

            # get new balance
            self.isolated_balance = self.get_isolated_balance(pair)

        if float(self.isolated_balance[0]["quoteAsset"]["free"]) != 0:
            # transfer back to SPOT account
            self.transfer_isolated_margin_to_spot(
                asset=quote,
                symbol=pair,
                amount=self.isolated_balance[0]["quoteAsset"]["free"],
            )
        if float(self.isolated_balance[0]["baseAsset"]["free"]) != 0:
            self.transfer_isolated_margin_to_spot(
                asset=base,
                symbol=pair,
                amount=self.isolated_balance[0]["baseAsset"]["free"],
            )

        if borrowed_amount == 0:
            # Funds are transferred back by now,
            # disabling pair should be done by cronjob,
            # therefore no reason not to complete the bot
            if hasattr(self, "active_bot"):
                self.active_bot.status = Status.completed

            self.disable_isolated_margin_account(pair)
            raise MarginLoanNotFound("Isolated margin loan already liquidated")

        return buy_margin_response

    def render_market_domination_reversal(self):
        """
        We want to know when it's more suitable to do long positions
        when it's more suitable to do short positions
        For now setting threshold to 70% i.e.
        if > 70% of assets in a given market (USDT) dominated by gainers
        if < 70% of assets in a given market dominated by losers
        Establish the timing
        """
        now = datetime.now()
        if now.minute == 0:
            data = self.get_market_domination_series()
            # reverse to make latest series more important
            data["data"]["gainers_count"].reverse()
            data["data"]["losers_count"].reverse()
            gainers_count = data["data"]["gainers_count"]
            losers_count = data["data"]["losers_count"]
            self.market_domination_trend = None
            if gainers_count[-1] > losers_count[-1]:
                self.market_domination_trend = "gainers"

                # Check reversal
                if gainers_count[-2] < losers_count[-2]:
                    # Positive reversal
                    self.market_domination_reversal = True

            else:
                self.market_domination_trend = "losers"

                if gainers_count[-2] > losers_count[-2]:
                    # Negative reversal
                    self.market_domination_reversal = False

        pass
