from api.databases.crud.autotrade_crud import AutotradeCrud
from api.tools.handle_error import json_response_message
from tools.exceptions import BinbotErrors
from account.abstract import AccountAbstract
from time import sleep
from tools.exceptions import BinanceErrors, LowBalanceCleanupError
from typing import Sequence
from databases.tables.bot_table import BotTable
from tools.enum_definitions import Status
from databases.crud.bot_crud import BotTableCrud
from databases.utils import independent_session
from databases.crud.symbols_crud import SymbolsCrud
from databases.crud.balances_crud import BalancesCrud
from orders.controller import OrderFactory
from exchange_apis.binance.orders import OrderControllerAbstract
from exchange_apis.binance.base import BinanceApi
from tools.maths import round_numbers, ts_to_day
from account.schemas import BalanceSeries
from datetime import datetime
from tools.enum_definitions import BinanceKlineIntervals


class BinanceAccount(AccountAbstract):
    """
    Binance-specific implementation of AccountAbstract.

    Inherits common methods from AccountAbstract and
    Binance API methods from BinbotApi.
    """

    def __init__(self, session):
        if session is None:
            session = independent_session()

        self.autotrade_settings = AutotradeCrud().get_settings()
        self.fiat = self.autotrade_settings.fiat
        self.bot_crud = BotTableCrud(session=session)
        self.usd_balance = 0
        self.fiat = AutotradeCrud().get_settings().fiat
        self.exception_list: list[str] = ["NFT", "BNB"]
        self.exception_list.append(self.fiat)
        self.bot_crud = BotTableCrud(session=session)
        self.balances_controller = BalancesCrud(session=session)
        self.symbols_crud = SymbolsCrud(session=session)
        controller, _ = OrderFactory().get_controller()
        self.controller: OrderControllerAbstract = controller
        self.api = BinanceApi()

        """
    In order to create benchmark charts,
    gaps in the balances' dates need to match with BTC dates
    """

    def consolidate_dates(self, klines, balance_date, i: int = 0) -> int | None:
        if i == len(klines):
            return None

        balance_date_day = ts_to_day(balance_date)

        for idx, d in enumerate(klines):
            kline_day = datetime.fromtimestamp(d[6] / 1000).strftime("%Y-%m-%d")

            # Match balance store dates with btc price dates
            if kline_day == balance_date_day:
                return idx
        else:
            return None

    def get_raw_balance(self) -> list:
        """
        Unrestricted balance
        """
        data = self.api.get_account_balance()
        balances = []
        for item in data["balances"]:
            if float(item["free"]) > 0 or float(item["locked"]) > 0:
                balances.append(item)
        return balances

    def get_single_spot_balance(self, asset) -> float:
        data = self.api.get_account_balance()
        for x in data["balances"]:
            if x["asset"] == asset:
                return float(x["free"])
        return 0

    def get_single_raw_balance(self, asset, fiat="USDC") -> float:
        """
        Get both SPOT balance and ISOLATED MARGIN balance
        """
        data = self.api.get_account_balance()
        for x in data["balances"]:
            if x["asset"] == asset:
                return float(x["free"])
        else:
            symbol = asset + fiat
            data = self.api.get_isolated_balance(symbol)
            if len(data) > 0:
                qty = float(data[0]["baseAsset"]["free"]) + float(
                    data[0]["baseAsset"]["borrowed"]
                )
                if qty > 0:
                    return qty
        return 0

    def get_margin_balance(self, symbol="BTC") -> float:
        # Response after request
        data = self.api.get_isolated_balance(symbol)
        symbol_balance = next((x["free"] for x in data if x["asset"] == symbol), 0)
        return symbol_balance

    def map_balance_with_benchmark(self, start_date, end_date) -> BalanceSeries:
        balance_series = self.balances_controller.query_balance_series(
            start_date=start_date, end_date=end_date
        )

        if len(balance_series) == 0:
            raise BinbotErrors("No balance data found.")

        # btc candlestick data series
        end_time = int(
            (
                datetime.fromtimestamp(balance_series[0].id / 1000)
                .replace(hour=0, minute=0, second=0)
                .timestamp()
            )
            * 1000
        )
        klines = self.api.get_raw_klines(
            limit=len(balance_series),
            symbol="BTCUSDC",
            interval=BinanceKlineIntervals.one_day,
            end_time=end_time,
        )

        balances_series_diff = []
        balances_series_dates = []
        balance_btc_diff = []

        for index, item in enumerate(balance_series):
            btc_index = self.consolidate_dates(klines, item.id, index)
            if btc_index is not None:
                if hasattr(balance_series[index], "estimated_total_fiat"):
                    balances_series_diff.append(
                        round_numbers(balance_series[index].estimated_total_fiat, 4)
                    )
                    time: int = klines[btc_index][6]
                    balances_series_dates.append(time)
                    balance_btc_diff.append(float(klines[btc_index][4]))
            else:
                continue

        # Reverse data so it shows latest in the graph on the right side.
        balances_series_diff.reverse()
        balances_series_dates.reverse()
        balance_btc_diff.reverse()

        return BalanceSeries(
            usdc=balances_series_diff, btc=balance_btc_diff, dates=balances_series_dates
        )

    def clean_balance_assets(self, bypass=False) -> list[str]:
        """
        Check if there are many small assets (0.000.. BTC)
        if there are more than 5 (number of bots)
        transfer to BNB
        """
        data = self.api.get_account_balance()
        all_symbols = self.symbols_crud.get_all()
        assets = []

        active_bots: Sequence[BotTable] = self.bot_crud.get(status=Status.active)
        for bot in active_bots:
            base_asset = bot.pair.replace(bot.quote_asset, "")
            self.exception_list.append(base_asset)

        for item in data["balances"]:
            if item["asset"] not in self.exception_list and float(item["free"]) > 0:
                assets.append(item["asset"])

        if len(assets) < 5 and not bypass:
            raise LowBalanceCleanupError(
                "Amount of assets in balance is low. Transfer not needed."
            )
        else:
            try:
                all_symbol_ids = {s.base_asset for s in all_symbols}
                idle_assets = [
                    a
                    for a in (all_symbol_ids & set(assets))
                    if a not in self.exception_list
                ]
                if self.fiat in idle_assets:
                    idle_assets.remove(self.fiat)
                self.api.transfer_dust(idle_assets)

                # Pause to make sure dust transfer is processed
                sleep(3)
                data = self.api.get_account_balance()
                available_bnb = next(
                    (
                        float(item["free"])
                        for item in data["balances"]
                        if item["asset"] == "BNB"
                    ),
                    0,
                )

                if available_bnb == 0:
                    return assets

                # Transfer dust endpoint always converts to BNB
                self.order.buy_order(symbol=f"BNB{self.fiat}", qty=available_bnb)
            except BinanceErrors as error:
                if error.code == -5005:
                    for asset in assets:
                        for string in error.message.split():
                            if asset == string:
                                self.exception_list.append(asset)
                                break
                    self.clean_balance_assets(bypass=bypass)
                else:
                    raise error

        return assets

    def get_total_fiat(self):
        """
        Simplified version of balance_estimate

        Returns:
            float: total BTC estimated in the SPOT wallet
            then converted into USDC
        """
        wallet_balance = self.api.get_wallet_balance()
        get_usdc_btc_rate = self.api.get_ticker_price(symbol=f"BTC{self.fiat}")
        total_balance: float = 0
        rate = float(get_usdc_btc_rate)
        for item in wallet_balance:
            if item["activate"]:
                total_balance += float(item["balance"])

        total_fiat = total_balance * rate
        return total_fiat

    def get_available_fiat(self):
        """
        Simplified version of balance_estimate
        to get free/avaliable USDC.

        Getting the total USDC directly
        from the balances because if it were e.g.
        Margin trading, it would not be available for use.
        The only available fiat is the unused USDC in the SPOT wallet.

        Balance not used in Margin trading should be
        transferred back to the SPOT wallet.

        Returns:
            str: total USDC available to
        """
        total_balance = self.get_raw_balance()
        for item in total_balance:
            if item["asset"] == self.fiat:
                return float(item["free"])
        else:
            return 0

    def disable_isolated_accounts(self):
        """
        Check and disable isolated accounts
        """
        info = self.api.get_isolated_balance()
        msg = "Disabling isolated margin account not required yet."
        for item in info["assets"]:
            # Liquidate price = 0 guarantees there is no loan unpaid
            if float(item["liquidatePrice"]) == 0:
                if float(item["baseAsset"]["free"]) > 0:
                    self.api.transfer_isolated_margin_to_spot(
                        asset=item["baseAsset"]["asset"],
                        symbol=item["symbol"],
                        amount=float(item["baseAsset"]["free"]),
                    )

                if float(item["quoteAsset"]["free"]) > 0:
                    self.api.transfer_isolated_margin_to_spot(
                        asset=item["quoteAsset"]["asset"],
                        symbol=item["symbol"],
                        amount=float(item["quoteAsset"]["free"]),
                    )

                self.api.disable_isolated_margin_account(item["symbol"])
                msg = "Sucessfully finished disabling isolated margin accounts."

        return json_response_message(msg)
