from typing import Tuple, Type, Union
from bots.models import BotModel
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.bot_crud import BotTableCrud
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from pybinbot.maths import round_numbers, round_numbers_ceiling
from tools.exceptions import (
    BinanceErrors,
    DealCreationError,
    InsufficientBalance,
    MarginLoanNotFound,
    BinbotErrors,
)
from pybinbot.enum import Status, Strategy, OrderStatus
from exchange_apis.binance.orders import BinanceOrderController

# To be removed one day en commission endpoint found that provides this value
ESTIMATED_COMMISSIONS_RATE = 0.0075


class BaseDeal(BinanceOrderController):
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
        super().__init__()
        self.controller: Union[PaperTradingTableCrud, BotTableCrud]
        if db_table == PaperTradingTable:
            self.controller = PaperTradingTableCrud()
        else:
            self.controller = BotTableCrud()
        self.active_bot = bot
        self.symbols_crud = SymbolsCrud()
        self.market_domination_reversal: bool | None = None
        self.symbol_info = self.symbols_crud.get_symbol(bot.pair)
        self.price_precision = self.symbol_info.price_precision
        self.qty_precision = self.symbol_info.qty_precision

        if bot.quote_asset.is_fiat():
            self.quote_qty_precision = self.calculate_qty_precision(
                bot.fiat + bot.quote_asset.value
            )

        elif bot.quote_asset != bot.fiat:
            self.quote_qty_precision = self.calculate_qty_precision(
                bot.quote_asset.value + bot.fiat
            )
        else:
            self.quote_qty_precision = self.calculate_qty_precision(bot.pair)

    def __repr__(self) -> str:
        """
        To check that BaseDeal works for all children classes
        """
        return f"BaseDeal({self.__dict__})"

    def compute_qty(self, pair: str) -> float:
        """
        Helper function to compute buy_price.
        """

        asset = self.symbols_crud.base_asset(pair)
        balance = self.get_single_spot_balance(asset)
        if balance == 0 and self.active_bot.strategy == Strategy.margin_short:
            # If spot balance is not found
            # try to get isolated margin balance
            balance = self.get_margin_balance(asset)
            if not balance or balance == 0:
                return 0

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
            + (
                float(self.isolated_balance[0]["baseAsset"]["borrowed"])
                * ESTIMATED_COMMISSIONS_RATE
            )
        )

        qty = round_numbers_ceiling(qty, self.qty_precision)
        free = float(self.isolated_balance[0]["baseAsset"]["free"])

        return qty, free

    def replace_order(self, cancel_order_id):
        payload = {
            "symbol": self.active_bot.pair,
            "quantity": self.active_bot.deal.base_order_size,
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
            if order["status"] == OrderStatus.NEW:
                self.signed_request(
                    self.order_url,
                    method="DELETE",
                    payload={"symbol": symbol, "orderId": order["orderId"]},
                )
                for bot_order in self.active_bot.orders:
                    if bot_order.order_id == order["orderId"]:
                        self.active_bot.orders.remove(order)
                        self.active_bot.add_log(
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
            start_time=int(self.active_bot.deal.opening_timestamp),
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
        if not self.isolated_balance:
            raise BinbotErrors("No isolated margin found for pair")

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

            if free == 0 or free < repay_amount:
                try:
                    qty = round_numbers_ceiling(repay_amount - free, self.qty_precision)
                    buy_margin_response = self.buy_margin_order(
                        symbol=self.active_bot.pair,
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
                        price = self.match_qty_engine(
                            symbol=pair, order_side=True, qty=qty
                        )
                        usdc_notional = price * qty
                        if usdc_notional < 15:
                            qty = round_numbers_ceiling(15 / price)

                        buy_margin_response = self.buy_margin_order(
                            pair, round_numbers(qty, self.qty_precision)
                        )
                        repay_amount, free = self.compute_margin_buy_back()
                        pass
            else:
                msg = "Unable to match isolated balance with repay amount"
                self.controller.update_logs(msg, self.active_bot)
                raise MarginLoanNotFound(msg)

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
