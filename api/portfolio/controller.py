from datetime import datetime
from math import sqrt
from typing import Union
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.balances_crud import BalancesCrud
from pybinbot import (
    BinanceApi,
    BinanceKlineIntervals,
    BinbotErrors,
    ExchangeId,
    KucoinApi,
    KucoinKlineIntervals,
    round_numbers,
    ts_to_day,
)
from sqlmodel import Session
from tools.config import Config
from portfolio.models import BenchmarkData, BenchmarkSeries, Stats


class PortfolioController:
    def __init__(self, session: Session):
        self.session = session
        self.config = Config()
        self.autotrade_settings = AutotradeCrud(session=session).get_settings()
        self.exchange = ExchangeId(self.autotrade_settings.exchange_id)
        self.fiat = self.autotrade_settings.fiat
        self.balances_crud = BalancesCrud(session=session)
        self.binance_api = BinanceApi(
            key=self.config.binance_key,
            secret=self.config.binance_secret,
        )
        self.kucoin_api = KucoinApi(
            key=self.config.kucoin_key,
            secret=self.config.kucoin_secret,
            passphrase=self.config.kucoin_passphrase,
        )
        self.api: Union[BinanceApi, KucoinApi] = self._default_api()
        self.benchmark_symbol = self.get_benchmark_symbol()
        self.interval = self.benchmark_interval()

    def _default_api(self) -> Union[BinanceApi, KucoinApi]:
        if self.exchange == ExchangeId.KUCOIN:
            return self.kucoin_api
        return self.binance_api

    def get_benchmark_symbol(self) -> str:
        benchmark_symbol = f"BTC{self.fiat}"
        if self.exchange == ExchangeId.KUCOIN:
            return f"BTC-{self.fiat}"
        return benchmark_symbol

    def benchmark_interval(self) -> str:
        if self.exchange == ExchangeId.KUCOIN:
            return KucoinKlineIntervals.ONE_DAY.value
        return BinanceKlineIntervals.one_day.value

    def _consolidate_dates(self, klines: list[list], balance_date: int) -> int | None:
        balance_date_day = ts_to_day(balance_date)

        for idx, kline in enumerate(klines):
            kline_day = datetime.fromtimestamp(kline[6] / 1000).strftime("%Y-%m-%d")
            if kline_day == balance_date_day:
                return idx

        return None

    def compute_sharpe(self, balances: list[float]) -> float:
        if len(balances) < 2:
            return 0.0

        returns: list[float] = []
        for idx in range(1, len(balances)):
            previous_balance = balances[idx - 1]
            current_balance = balances[idx]
            if previous_balance == 0:
                continue
            returns.append((current_balance - previous_balance) / previous_balance)

        if len(returns) < 2:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum((value - mean_return) ** 2 for value in returns) / len(returns)
        std_return = variance**0.5

        if std_return == 0:
            return 0.0

        sharpe = (mean_return / std_return) * sqrt(365)
        return round_numbers(sharpe, 4)

    def map_balance_with_benchmark(
        self, start_date: int, end_date: int
    ) -> BenchmarkSeries:
        """
        Subtitute for Assets.map_balance_with_benchmark

        Emancipates the portfolio logic out of the Binance directory, as this is exchange agnostic, adds new Sharpe Ratio and Pnl as part of the data.
        """

        balance_series = self.balances_crud.query_balance_series(
            start_date=start_date,
            end_date=end_date,
        )

        if len(balance_series) == 0:
            raise BinbotErrors("No balance data found.")

        oldest_balance = balance_series[-1]
        end_time = int(
            datetime.fromtimestamp(oldest_balance.id / 1000)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
            * 1000
        )

        klines = self.api.get_ui_klines(
            symbol=self.benchmark_symbol,
            interval=self.interval,
            limit=len(balance_series),
            end_time=end_time,
        )

        fiat_series: list[float] = []
        btc_series: list[float] = []
        dates: list[int] = []
        balances: list[float] = []

        for item in balance_series:
            if item.estimated_total_fiat is not None:
                balances.append(float(item.estimated_total_fiat))

            btc_index = self._consolidate_dates(klines, item.id)
            if btc_index is None or item.estimated_total_fiat is None:
                continue

            fiat_series.append(round_numbers(float(item.estimated_total_fiat), 4))
            btc_series.append(float(klines[btc_index][4]))
            dates.append(int(klines[btc_index][6]))

        fiat_series.reverse()
        btc_series.reverse()
        dates.reverse()
        balances.reverse()

        pnl = 0.0
        if len(balances) >= 2:
            pnl = round_numbers(balances[-1] - balances[0], 4)

        stats = Stats(
            pnl=pnl,
            sharpe=self.compute_sharpe(balances),
        )
        series = BenchmarkData(
            fiat=fiat_series,
            btc=btc_series,
            dates=dates,
        )

        benchmark_series = BenchmarkSeries(
            series=series,
            stats=stats,
        )
        return benchmark_series
