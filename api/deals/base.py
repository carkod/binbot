from typing import Tuple, Type, Union
from datetime import datetime
from bots.models import BotModel
from database.models.bot_table import BotTable, PaperTradingTable
from database.bot_crud import BotTableCrud
from database.paper_trading_crud import PaperTradingTableCrud
from orders.controller import OrderController
from tools.round_numbers import round_numbers, round_numbers_ceiling
from tools.exceptions import (
    BinanceErrors,
    DealCreationError,
    InsufficientBalance,
    MarginLoanNotFound,
)
from tools.enum_definitions import Status, Strategy
from base_producer import BaseProducer


# To be removed one day en commission endpoint found that provides this value
ESTIMATED_COMMISSIONS_RATE = 0.0075


class BaseDeal(OrderController):
    """
    Base Deal class to unify common functionality for
    both DealAbstract and MarginDeal/SpotDeal.

    Deals should always deal with the same symbol
    at instance creation level, since it needs
    an active_bot for instantiation. Thus,
    self.symbol is always the same.
    """

    def __init__(
        self,
        bot: BotModel,
        db_table: Type[Union[PaperTradingTable, BotTable]] = BotTable,
    ):
        db_controller: Type[Union[PaperTradingTableCrud, BotTableCrud]]
        if db_table == PaperTradingTable:
            db_controller = PaperTradingTableCrud
        else:
            db_controller = BotTableCrud

        self.controller = db_controller()
        self.active_bot = bot
        self.market_domination_reversal: bool | None = None
        self.price_precision = self.calculate_price_precision(bot.pair)
        self.qty_precision = self.calculate_qty_precision(bot.pair)
        self.base_producer = BaseProducer()
        self.producer = self.base_producer.start_producer()

        if self.active_bot.strategy == Strategy.margin_short:
            self.isolated_balance = self.get_isolated_balance(self.active_bot.pair)

    def __repr__(self) -> str:
        """
        To check that BaseDeal works for all children classes
        """
        return f"BaseDeal({self.__dict__})"

    def compute_qty(self, pair):
        """
        Helper function to compute buy_price.
        """

        asset = self.find_baseAsset(pair)
        balance = self.get_single_raw_balance(asset)
        if balance == 0:
            # If spot balance is not found
            # try to get isolated margin balance
            free = self.get_margin_balance(asset)
            qty = round_numbers(free, self.qty_precision)
            if not free:
                return None

        qty = round_numbers(balance, self.qty_precision)
        return qty

    def compute_margin_buy_back(self) -> Tuple[float | int, float | int]:
        """
        Same as compute_qty but with isolated margin balance

        Find available amount to buy_back
        this is the borrowed amount + interests.
        Decimals have to be rounded up to avoid leaving
        "leftover" interests
        """
        qty: float = 0
        free: float = 0

        if (
            self.isolated_balance[0]["quoteAsset"]["free"] == 0
            or self.isolated_balance[0]["baseAsset"]["borrowed"] == 0
        ):
            return qty, free

        qty = (
            float(self.isolated_balance[0]["baseAsset"]["borrowed"])
            + float(self.isolated_balance[0]["baseAsset"]["interest"])
            + float(self.isolated_balance[0]["baseAsset"]["borrowed"])
            * ESTIMATED_COMMISSIONS_RATE
        )

        qty = round_numbers_ceiling(qty, self.qty_precision)
        free = float(self.isolated_balance[0]["baseAsset"]["free"])

        return qty, free

    def replace_order(self, cancel_order_id):
        payload = {
            "symbol": self.active_bot.pair,
            "quantity": self.active_bot.base_order_size,
            "cancelOrderId": cancel_order_id,
            "type": "MARKET",
            "side": "SELL",
            "cancelReplaceMode": "ALLOW_FAILURE",
        }
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
                        self.active_bot.orders.remove(order)
                        self.active_bot.logs.append(
                            "base_order not executed, therefore cancelled"
                        )
                        self.active_bot.status = Status.error
                        self.controller.save(self.active_bot)
                        break

                return True
        return False

    def verify_deal_close_order(self):
        """
        Check if deal is closed by checking
        if there are any SELL orders
        """
        all_orders = self.get_all_orders(
            self.active_bot.pair,
            start_time=float(self.active_bot.deal.opening_timestamp),
        )
        for order in all_orders:
            if (
                order["side"] == "SELL"
                and float(order["price"]) == self.active_bot.deal.take_profit_price
                and float(order["origQty"]) == self.active_bot.deal.opening_qty
            ):
                return order

        return None

    def margin_liquidation(self, pair: str):
        """
        Emulate Binance Dashboard One click liquidation function

        Args:
        - pair: a.k.a symbol, quote asset + base asset
        - qty_precision: to round numbers for Binance  Passed optionally to
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
            repay_amount = round_numbers_ceiling(repay_amount, self.qty_precision)

            if free == 0 or free < repay_amount:
                try:
                    # lot_size_by_symbol = self.lot_size_by_symbol(pair, "stepSize")
                    qty = round_numbers_ceiling(repay_amount - free, self.qty_precision)
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
                        available_balance = self.get_single_raw_balance(quote)
                        amount_to_transfer: float = 15  # Min amount
                        if available_balance < 15:
                            amount_to_transfer = available_balance
                        self.transfer_spot_to_isolated_margin(
                            asset=quote,
                            symbol=pair,
                            amount=amount_to_transfer,
                        )
                        buy_margin_response = self.buy_margin_order(
                            pair,
                            round_numbers(transfer_diff_qty, self.qty_precision),
                        )
                        repay_amount, free = self.compute_margin_buy_back()
                        pass
                    if error.code == -2010 or error.code == -1013:
                        # There is already money in the base asset
                        qty = round_numbers_ceiling(
                            repay_amount - free, self.qty_precision
                        )
                        price = float(self.matching_engine(pair, True, qty))
                        usdc_notional = price * qty
                        if usdc_notional < 15:
                            qty = round_numbers_ceiling(15 / price)

                        buy_margin_response = self.buy_margin_order(
                            pair, round_numbers(qty, self.qty_precision)
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

    def spot_liquidation(self, pair: str):
        qty = self.compute_qty(pair)
        if qty > 0:
            order_res = self.sell_order(pair, qty)
            return order_res
        else:
            raise InsufficientBalance(
                "Not enough balance to liquidate. Most likely bot closed already"
            )

    def render_market_domination_reversal(self):
        """
        We want to know when it's more suitable to do long positions
        when it's more suitable to do short positions
        For now setting threshold to 70% i.e.
        if > 70% of assets in a given market (USDC) dominated by gainers
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
