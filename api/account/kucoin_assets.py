from datetime import datetime, timedelta
from account.kucoin_account import KucoinAccount
from databases.crud.symbols_crud import SymbolsCrud
from databases.crud.balances_crud import BalancesCrud
from databases.tables.bot_table import BotTable
from databases.crud.autotrade_crud import AutotradeCrud
from bots.models import BotModel
from deals.abstractions.factory import DealAbstract
from tools.handle_error import json_response
from tools.maths import ts_to_day
from tools.enum_definitions import Status, Strategy
from databases.crud.bot_crud import BotTableCrud
from account.schemas import BalanceSeries
from tools.exceptions import BinbotErrors


class KucoinAssets(KucoinAccount):
    """
    KuCoin Assets class inherits from KucoinAccount

    These are entities that are dependent on KuCoin's account API.
    Similar to the Assets class for Binance, but adapted for KuCoin API structure.

    Note: KuCoin has different API structure and endpoints compared to Binance.
    Some methods may need significant adaptation or may not have direct equivalents.
    """

    def __init__(self, session):
        super().__init__()
        self.usd_balance = 0
        self.fiat = AutotradeCrud().get_settings().fiat
        self.exception_list: list[str] = ["NFT", "KCS"]  # KCS is KuCoin's native token
        self.exception_list.append(self.fiat)
        self.bot_controller = BotTableCrud(session=session)
        self.balances_controller = BalancesCrud(session=session)
        self.symbols_crud = SymbolsCrud(session=session)

    def get_pnl(self, days=7):
        """
        Get profit and loss data for the specified number of days
        """
        current_time = datetime.now()
        start = current_time - timedelta(days=days)
        ts = int(start.timestamp())
        end_ts = int(current_time.timestamp())
        data = self.balances_controller.query_balance_series(ts, end_ts)

        resp = json_response({"data": data})
        return resp

    def _check_locked(self, b):
        """
        Check locked balance
        KuCoin structure might differ - they use 'available' and 'holds'
        """
        qty: float = 0
        if "holds" in b:
            qty = float(b["available"]) + float(b["holds"])
        elif "locked" in b:
            qty = float(b.get("free", b.get("available", 0))) + float(b["locked"])
        else:
            qty = float(b.get("free", b.get("available", 0)))
        return qty

    def store_balance(self) -> dict:
        """
        Alternative PnL data that runs as a cronjob everyday once at 12:00.
        This works outside of context.

        Stores current balance in DB and estimated
        total balance in fiat (USDC) for the day.

        Note: KuCoin API structure differs from Binance
        """
        # Note: These methods need to be implemented in KucoinAccount
        raise NotImplementedError(
            "store_balance needs KuCoin API methods to be implemented"
        )

    def balance_estimate(self):
        """
        Estimated balance in given fiat coin
        Note: KuCoin uses different account structure than Binance
        """
        raise NotImplementedError(
            "balance_estimate needs KuCoin API methods to be implemented"
        )

    async def retrieve_gainers_losers(self, market_asset="USDC"):
        """
        Create and return a ranking with gainers vs losers data
        Note: KuCoin has different 24hr ticker structure
        """
        # Note: This would need to be implemented in KucoinApi
        # KuCoin uses get_24hr_stats for all symbols
        raise NotImplementedError(
            "retrieve_gainers_losers needs KuCoin API methods to be implemented"
        )

    def consolidate_dates(self, klines, balance_date, i: int = 0) -> int | None:
        """
        In order to create benchmark charts,
        gaps in the balances' dates need to match with BTC dates
        """
        if i == len(klines):
            return None

        balance_date_day = ts_to_day(balance_date)

        for idx, d in enumerate(klines):
            # KuCoin kline structure: [timestamp, open, close, high, low, volume, amount]
            kline_day = datetime.fromtimestamp(d[0] / 1000).strftime("%Y-%m-%d")

            # Match balance store dates with btc price dates
            if kline_day == balance_date_day:
                return idx
        else:
            return None

    def map_balance_with_benchmark(self, start_date, end_date) -> BalanceSeries:
        """
        Map balance series with BTC benchmark for comparison charts
        """
        balance_series = self.balances_controller.query_balance_series(
            start_date=start_date, end_date=end_date
        )

        if len(balance_series) == 0:
            raise BinbotErrors("No balance data found.")

        # Note: KuCoin uses different kline format and endpoints
        # This would need to be implemented with KuCoin's get_klines method
        raise NotImplementedError(
            "map_balance_with_benchmark needs KuCoin klines API to be implemented"
        )

    def clean_balance_assets(self, bypass=False) -> list[str]:
        """
        Check if there are many small assets
        KuCoin doesn't have a dust conversion feature like Binance's transfer to BNB
        This method would need to be adapted for KuCoin's features
        """
        # Note: KuCoin has different small balance handling
        # They may have inner transfer or different mechanisms
        raise NotImplementedError("clean_balance_assets needs to be adapted for KuCoin")

    def get_total_fiat(self):
        """
        Simplified version of balance_estimate

        Returns:
            float: total BTC estimated in the SPOT wallet
            then converted into USDC
        """
        # Note: KuCoin account structure differs
        raise NotImplementedError(
            "get_total_fiat needs KuCoin API methods to be implemented"
        )

    def get_available_fiat(self):
        """
        Simplified version of balance_estimate
        to get free/available USDC.

        Getting the total USDC directly
        from the balances because if it were e.g.
        Margin trading, it would not be available for use.

        Note: KuCoin uses 'available' instead of 'free'
        """
        # Note: This needs KuCoin's get_account_list or get_account implementation
        raise NotImplementedError(
            "get_available_fiat needs KuCoin API methods to be implemented"
        )

    def disable_isolated_accounts(self):
        """
        Check and disable isolated accounts
        Note: KuCoin has different margin account structure than Binance
        """
        # KuCoin margin works differently - isolated margin may not have same disable feature
        raise NotImplementedError(
            "disable_isolated_accounts needs to be adapted for KuCoin margin"
        )

    def one_click_liquidation(
        self, pair: str, bot_strategy: str = "margin", bypass_check: bool = False
    ) -> BotTable | None:
        """
        Emulate KuCoin Dashboard
        One click liquidation function

        This endpoint is different than the margin_liquidation function
        in that it contains some clean up functionality in the cases
        where there are are still funds in the isolated pair.

        Note: KuCoin symbol format uses hyphen (BTC-USDT) instead of Binance format (BTCUSDT)
        """
        strategy = Strategy.margin_short if bot_strategy == "margin" else Strategy.long

        bot = self.bot_controller.get_one(
            symbol=pair, strategy=strategy, status=Status.all
        )

        if not bot:
            return bot

        active_bot = BotModel.dump_from_table(bot)
        deal = DealAbstract(active_bot, db_table=BotTable)

        if strategy == Strategy.margin_short:
            # Note: This would need KuCoin margin liquidation implementation
            deal.margin_liquidation(pair)
        else:
            # Note: This would need KuCoin spot liquidation implementation
            deal.spot_liquidation(pair)

        return bot
