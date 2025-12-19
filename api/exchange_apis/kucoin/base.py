from kucoin_universal_sdk.generate.spot.market import (
    GetPartOrderBookReqBuilder,
    GetAllSymbolsReqBuilder,
    GetKlinesReqBuilder,
)
from kucoin_universal_sdk.generate.account.account import (
    GetSpotAccountListReqBuilder,
    GetIsolatedMarginAccountReqBuilder,
)
from kucoin_universal_sdk.generate.account.account.model_get_isolated_margin_account_resp import (
    GetIsolatedMarginAccountResp,
)
from tools.enum_definitions import KucoinKlineIntervals
from exchange_apis.kucoin.orders import KucoinOrders


class KucoinApi(KucoinOrders):
    def __init__(self):
        self.client = self.setup_client()
        self.spot_api = self.client.rest_service().get_spot_service().get_market_api()
        self.account_api = (
            self.client.rest_service().get_account_service().get_account_api()
        )

    def get_all_symbols(self):
        request = GetAllSymbolsReqBuilder().build()
        response = self.spot_api.get_all_symbols(request)
        return response

    def get_ticker_price(self, symbol: str) -> float:
        request = GetPartOrderBookReqBuilder().set_symbol(symbol).set_size("1").build()
        response = self.spot_api.get_ticker(request)
        return float(response.price)

    def get_account_balance(self):
        """
        Aggregate all balances from all account types (spot, main, trade, margin, futures).

        The right data shape for Kucion should be provided by
        get_account_balance_by_type method.

        However, this method provides a normalized version for backwards compatibility (Binance) and consistency with current balances table.

        Returns a dict:
            {
                asset:
                    {
                        total: float,
                        breakdown:
                            {
                                    account_type: float, ...
                            }
                    }
            }
        """
        spot_request = GetSpotAccountListReqBuilder().build()
        all_accounts = self.account_api.get_spot_account_list(spot_request)
        balance_items = dict()
        for item in all_accounts.data:
            if float(item.balance) > 0:
                balance_items[item.currency] = {
                    "balance": float(item.balance),
                    "free": float(item.available),
                    "locked": float(item.holds),
                }

        margin_request = GetIsolatedMarginAccountReqBuilder().build()
        margin_accounts = self.account_api.get_isolated_margin_account(margin_request)
        if float(margin_accounts.total_asset_of_quote_currency) > 0:
            balance_items["USDT"]["balance"] += float(
                margin_accounts.total_asset_of_quote_currency
            )

        return balance_items

    def get_account_balance_by_type(self):
        """
        Get balances grouped by account type.
        Returns:
            {
                'MAIN': {'USDT': {...}, 'BTC': {...}, ...},
                'TRADE': {'USDT': {...}, ...},
                'MARGIN': {...},
                ...
            }
        Each currency has: balance (total), available, holds
        """
        spot_request = GetSpotAccountListReqBuilder().build()
        all_accounts = self.account_api.get_spot_account_list(spot_request)

        balance_by_type: dict[str, dict[str, dict[str, float]]] = {}
        for item in all_accounts.data:
            if float(item.balance) > 0:
                account_type = item.type  # MAIN, TRADE, MARGIN, etc.
                if account_type not in balance_by_type:
                    balance_by_type[account_type] = {}
                balance_by_type[account_type][item.currency] = {
                    "balance": float(item.balance),
                    "available": float(item.available),
                    "holds": float(item.holds),
                }

        return balance_by_type

    def get_single_spot_balance(self, asset: str) -> float:
        spot_request = GetSpotAccountListReqBuilder().build()
        all_accounts = self.account_api.get_spot_account_list(spot_request)
        total_balance = 0.0
        for item in all_accounts.data:
            if item.currency == asset:
                return float(item.balance)

        return total_balance

    def get_isolated_balance(self, symbol: str) -> GetIsolatedMarginAccountResp:
        request = GetIsolatedMarginAccountReqBuilder().set_symbol(symbol).build()
        response = self.account_api.get_isolated_margin_account(request)
        return response

    def get_raw_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time=None,
        end_time=None,
    ):
        """
        Get raw klines/candlestick data from Kucoin.

        Args:
            symbol: Trading pair symbol (e.g., "BTC-USDT")
            interval: Kline interval (e.g., "15min", "1hour", "1day")
            limit: Number of klines to retrieve (max 1500, default 500)
            start_time: Start time in milliseconds (optional)
            end_time: End time in milliseconds (optional)

        Returns:
            List of klines in format compatible with Binance format:
            [timestamp, open, high, low, close, volume, close_time, ...]
        """
        builder = GetKlinesReqBuilder().set_symbol(symbol).set_type(interval)

        if start_time:
            builder = builder.set_start_at(int(start_time / 1000))
        if end_time:
            builder = builder.set_end_at(int(end_time / 1000))

        request = builder.build()
        response = self.spot_api.get_klines(request)

        interval_ms = KucoinKlineIntervals.get_interval_ms(interval)

        # Convert Kucoin format to Binance-compatible format
        # Kucoin returns: [time, open, close, high, low, volume, turnover]
        # Binance format: [open_time, open, high, low, close, volume, close_time, ...]
        klines = []
        if response.data:
            for k in response.data[:limit]:
                # k format: [timestamp(seconds), open, close, high, low, volume, turnover]
                open_time = int(k[0]) * 1000  # Convert to milliseconds
                close_time = open_time + interval_ms  # Calculate proper close time
                klines.append(
                    [
                        open_time,  # open_time in milliseconds
                        k[1],  # open
                        k[3],  # high
                        k[4],  # low
                        k[2],  # close
                        k[5],  # volume
                        close_time,  # close_time properly calculated
                    ]
                )

        return klines
