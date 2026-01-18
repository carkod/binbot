from exchange_apis.kucoin.rest import KucoinRest
from pybinbot import KucoinKlineIntervals
from datetime import datetime
from kucoin_universal_sdk.generate.spot.market import GetKlinesReqBuilder


class KucoinMarket(KucoinRest):
    """
    Convienience wrapper for Kucoin order operations.

    - Kucoin transactions don't immediately return all order details so we need cooldown slee
    """

    TRANSACTION_COOLDOWN_SECONDS = 1

    def __init__(self):
        super().__init__()
        self.client = self.setup_client()
        self.spot_api = self.client.rest_service().get_spot_service().get_market_api()

    def get_ui_klines(
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
        # Compute time window based on limit and interval
        interval_ms = KucoinKlineIntervals.get_interval_ms(interval)
        now_ms = int(datetime.now().timestamp() * 1000)
        # Align end_time to interval boundary
        end_time = now_ms - (now_ms % interval_ms)
        start_time = end_time - (limit * interval_ms)

        builder = (
            GetKlinesReqBuilder()
            .set_symbol(symbol)
            .set_type(interval)
            .set_start_at(start_time // 1000)
            .set_end_at(end_time // 1000)
        )

        request = builder.build()
        response = self.spot_api.get_klines(request)

        # Convert Kucoin format to Binance-compatible format
        # Kucoin returns: [time, open, close, high, low, volume, turnover]
        # Binance format: [open_time, open, high, low, close, volume, close_time, ...]
        klines = []
        if response.data:
            for k in response.data:
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
                        k[5],  # volume base asset
                        close_time,  # close_time properly calculated
                        k[6],  # volume quote asset
                    ]
                )
            klines.reverse()

        return klines
