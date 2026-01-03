from datetime import datetime, timedelta
from time import sleep
from exchange_apis.binance.orders import BinanceOrderController
from databases.crud.symbols_crud import SymbolsCrud
from databases.crud.balances_crud import BalancesCrud
from databases.tables.bot_table import BotTable
from databases.crud.autotrade_crud import AutotradeCrud
from bots.models import BotModel
from exchange_apis.binance.deals.factory import BinanceDeal
from tools.handle_error import json_response, json_response_message
from pybinbot.maths import (
    round_numbers,
)
from pybinbot.timestamps import ts_to_day
from tools.exceptions import BinanceErrors, LowBalanceCleanupError
from databases.crud.bot_crud import BotTableCrud
from account.schemas import BalanceSeries
from pybinbot.enum import BinanceKlineIntervals, Status, Strategy
from tools.exceptions import BinbotErrors
from typing import Sequence


class Assets(BinanceOrderController):
    """
    Assets class inherits from OrderController
    which inherits from Account class

    These are entities that are dependent on Binance's account API.

    The reason why we started to need OrderController
    is because clean_balance_assets needs to execute
    orders now to clean BNB dust. Assets class was previously using only the Account class
    """

    def __init__(self, session):
        self.usd_balance = 0
        self.autotrade_settings = AutotradeCrud(session=session).get_settings()
        self.fiat = self.autotrade_settings.fiat
        self.exception_list: list[str] = ["NFT", "BNB"]
        self.exception_list.append(self.fiat)
        self.bot_controller = BotTableCrud(session=session)
        self.balances_controller = BalancesCrud(session=session)
        self.symbols_crud = SymbolsCrud(session=session)

    def get_pnl(self, days=7):
        current_time = datetime.now()
        start = current_time - timedelta(days=days)
        ts = int(start.timestamp())
        end_ts = int(current_time.timestamp())
        data = self.balances_controller.query_balance_series(ts, end_ts)

        resp = json_response({"data": data})
        return resp

    def _check_locked(self, b):
        qty: float = 0
        if "locked" in b:
            qty = float(b["free"]) + float(b["locked"])
        else:
            qty = float(b["free"])
        return qty

    def store_balance(self) -> dict:
        """
        Alternative PnL data that runs as a cronjob everyday once at 12:00.
        This works outside of context.

        Stores current balance in DB and estimated
        total balance in fiat (USDC) for the day.

        Better than deprecated store_balance_snapshot
        - it doesn't required high weight
        - it can be tweaked to have our needed format
        - the result of total_usdc is pretty much the same, the difference is in 0.001 USDC
        - however we don't need a loop and we decreased one network request (also added one, because we still need the raw_balance to display charts)
        """
        wallet_balance = self.get_wallet_balance()
        itemized_balance = self.get_raw_balance()

        rate = self.get_ticker_price(f"BTC{self.fiat}")

        total_wallet_balance: float = 0
        for item in wallet_balance:
            if item["balance"] and float(item["balance"]) > 0:
                total_wallet_balance += float(item["balance"])

        total_fiat = total_wallet_balance * float(rate)
        response = self.balances_controller.create_balance_series(
            itemized_balance, round_numbers(total_fiat, 4)
        )
        return response

    def balance_estimate(self):
        """
        Estimated balance in given fiat coin
        """
        balances = self.get_raw_balance()
        total_fiat: float = 0
        left_to_allocate: float = 0
        total_isolated_margin: float = 0
        btc_rate = self.get_ticker_price(f"BTC{self.fiat}")
        wallet_balance = self.get_wallet_balance()
        for item in wallet_balance:
            if item["walletName"] == "Spot":
                total_fiat += float(item["balance"]) * float(btc_rate)
            if item["walletName"] == "Isolated Margin":
                total_isolated_margin += float(item["balance"]) * float(btc_rate)

        for b in balances:
            if b["asset"] == self.fiat:
                left_to_allocate = float(b["free"])
                break

        balance = {
            "balances": balances,
            "total_fiat": total_fiat + total_isolated_margin,
            "total_isolated_margin": total_isolated_margin,
            "fiat_left": left_to_allocate,
            "asset": self.fiat,
        }
        return balance

    async def retrieve_gainers_losers(self, market_asset="USDC"):
        """
        Create and return a ranking with gainers vs losers data
        """
        data = self.ticker_24()
        gainers_losers_list = [
            item for item in data if item["symbol"].endswith(market_asset)
        ]
        gainers_losers_list.sort(
            reverse=True, key=lambda item: float(item["priceChangePercent"])
        )

        return json_response(
            {
                "message": "Successfully retrieved gainers and losers data",
                "data": gainers_losers_list,
            }
        )

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
        klines = self.get_ui_klines(
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
        data = self.get_account_balance()
        all_symbols = self.symbols_crud.get_all()
        assets = []

        active_bots: Sequence[BotTable] = self.bot_controller.get(status=Status.active)
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
                self.transfer_dust(idle_assets)

                # Pause to make sure dust transfer is processed
                sleep(3)
                data = self.get_account_balance()
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
                self.buy_order(symbol=f"BNB{self.fiat}", qty=available_bnb)
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

    def disable_isolated_accounts(self):
        """
        Check and disable isolated accounts
        """
        info = self.signed_request(url=self.isolated_account_url, payload={})
        msg = "Disabling isolated margin account not required yet."
        for item in info["assets"]:
            # Liquidate price = 0 guarantees there is no loan unpaid
            if float(item["liquidatePrice"]) == 0:
                if float(item["baseAsset"]["free"]) > 0:
                    self.transfer_isolated_margin_to_spot(
                        asset=item["baseAsset"]["asset"],
                        symbol=item["symbol"],
                        amount=float(item["baseAsset"]["free"]),
                    )

                if float(item["quoteAsset"]["free"]) > 0:
                    self.transfer_isolated_margin_to_spot(
                        asset=item["quoteAsset"]["asset"],
                        symbol=item["symbol"],
                        amount=float(item["quoteAsset"]["free"]),
                    )

                self.disable_isolated_margin_account(item["symbol"])
                msg = "Sucessfully finished disabling isolated margin accounts."

        return json_response_message(msg)

    def one_click_liquidation(
        self, pair: str, bot_strategy: str = "margin", bypass_check: bool = False
    ) -> BotTable | None:
        """
        Emulate Binance Dashboard
        One click liquidation function

        This endpoint is different than the margin_liquidation function
        in that it contains some clean up functionality in the cases
        where there are are still funds in the isolated pair.
        Therefore, it should clean all bots with provided pairs without filtering
        by status.

        market arg is required, because there can be repeated
        pairs in both MARGIN and SPOT markets.
        """

        strategy = Strategy.margin_short if bot_strategy == "margin" else Strategy.long

        bot = self.bot_controller.get_one(
            symbol=pair, strategy=strategy, status=Status.all
        )

        if not bot:
            return bot

        active_bot = BotModel.dump_from_table(bot)
        deal = BinanceDeal(active_bot, db_table=BotTable)

        if strategy == Strategy.margin_short:
            deal.margin_liquidation(pair)
        else:
            deal.spot_liquidation(pair)

        return bot
