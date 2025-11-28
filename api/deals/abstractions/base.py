from typing import Tuple, Type, Union
from exchange_apis.api_protocol import ExchangeApiProtocol
from orders.abstract import OrderControllerAbstract
from bots.models import BotModel
from databases.tables.bot_table import BotTable, PaperTradingTable
from databases.crud.bot_crud import BotTableCrud
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from orders.controller import OrderFactory
from tools.maths import round_numbers, round_numbers_ceiling
from tools.exceptions import (
    BinanceErrors,
    InsufficientBalance,
    MarginLoanNotFound,
    BinbotErrors,
)
from tools.enum_definitions import Status, Strategy, OrderStatus
from apis import BinbotApi

# To be removed one day en commission endpoint found that provides this value
ESTIMATED_COMMISSIONS_RATE = 0.0075


class BaseDeal:
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
        db_controller: Type[Union[PaperTradingTableCrud, BotTableCrud]]
        self.order: OrderControllerAbstract = OrderFactory().get_order_controller()
        account, api = OrderFactory().get_account_controller()
        self.account = account
        self.api: ExchangeApiProtocol = api
        self.binbot_api = BinbotApi()
        if db_table == PaperTradingTable:
            db_controller = PaperTradingTableCrud
        else:
            db_controller = BotTableCrud

        self.controller = db_controller()
        self.active_bot = bot
        self.symbols_crud = SymbolsCrud()
        self.market_domination_reversal: bool | None = None
        self.symbol_info = self.symbols_crud.get_symbol(bot.pair)
        self.price_precision = self.symbol_info.price_precision
        self.qty_precision = self.symbol_info.qty_precision

        if bot.quote_asset.is_fiat():
            self.quote_qty_precision = self.order.calculate_qty_precision(
                bot.fiat + bot.quote_asset.value
            )

        elif bot.quote_asset != bot.fiat:
            self.quote_qty_precision = self.order.calculate_qty_precision(
                bot.quote_asset.value + bot.fiat
            )
        else:
            self.quote_qty_precision = self.order.calculate_qty_precision(bot.pair)

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
        balance = self.account.get_single_spot_balance(asset)
        if balance == 0 and self.active_bot.strategy == Strategy.margin_short:
            # If spot balance is not found
            # try to get isolated margin balance
            balance = self.account.get_margin_balance(asset)
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

    def close_open_orders(self, symbol):
        """
        Check open orders and replace with new
        """
        open_orders = self.api.query_open_orders(symbol)
        for order in open_orders:
            if order["status"] == OrderStatus.NEW:
                self.account.close_open_order(symbol, order["orderId"])
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
        all_orders = self.api.get_all_orders(
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
        self.isolated_balance = self.api.get_isolated_balance(pair)
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
                    buy_margin_response = self.order.buy_margin_order(
                        symbol=pair,
                        qty=qty,
                    )
                    repay_amount, free = self.compute_margin_buy_back()
                except BinanceErrors as error:
                    if error.code == -3041:
                        # Not enough funds in isolated pair
                        # transfer from wallet
                        transfer_diff_qty = round_numbers_ceiling(repay_amount - free)
                        available_balance = self.account.get_single_raw_balance(quote)
                        amount_to_transfer: float = 15  # Min amount
                        if available_balance < 15:
                            amount_to_transfer = available_balance
                        self.api.transfer_spot_to_isolated_margin(
                            asset=quote,
                            symbol=pair,
                            amount=amount_to_transfer,
                        )
                        buy_margin_response = self.order.buy_margin_order(
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
                        price = self.order.match_qty_engine(
                            symbol=pair, order_side=True, qty=qty
                        )
                        usdc_notional = price * qty
                        if usdc_notional < 15:
                            qty = round_numbers_ceiling(15 / price)

                        buy_margin_response = self.order.buy_margin_order(
                            pair, round_numbers(qty, self.qty_precision)
                        )
                        repay_amount, free = self.compute_margin_buy_back()
                        pass
            else:
                msg = "Unable to match isolated balance with repay amount"
                self.controller.update_logs(msg, self.active_bot)
                raise MarginLoanNotFound(msg)

            self.api.repay_margin_loan(
                asset=base,
                symbol=pair,
                amount=repay_amount,
                isIsolated="TRUE",
            )

            # get new balance
            self.isolated_balance = self.api.get_isolated_balance(pair)

        if float(self.isolated_balance[0]["quoteAsset"]["free"]) != 0:
            # transfer back to SPOT account
            self.api.transfer_isolated_margin_to_spot(
                asset=quote,
                symbol=pair,
                amount=self.isolated_balance[0]["quoteAsset"]["free"],
            )
        if float(self.isolated_balance[0]["baseAsset"]["free"]) != 0:
            self.api.transfer_isolated_margin_to_spot(
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

            self.api.disable_isolated_margin_account(pair)
            raise MarginLoanNotFound("Isolated margin loan already liquidated")

        return buy_margin_response

    def spot_liquidation(self, pair: str):
        qty = self.compute_qty(pair)
        if qty > 0:
            order_res = self.order.sell_order(pair, qty)
            return order_res
        else:
            raise InsufficientBalance(
                "Not enough balance to liquidate. Most likely bot closed already"
            )
