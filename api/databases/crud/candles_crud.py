import logging
from exchange_apis.binance import BinanceApi
from databases.db import setup_kafka_db
from pandas import DataFrame
import pandas as pd
from tools.enum_definitions import BinanceKlineIntervals
from tools.round_numbers import round_numbers
from databases.crud.symbols_crud import SymbolsCrud
from datetime import datetime, timezone


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class CandlesCrud:
    """
    CRUD operations for candles collection using timeseries with 1-month TTL
    Stores data in millisecond timestamps format for better performance
    """

    def __init__(self) -> None:
        super().__init__()
        self.db = setup_kafka_db()
        self.binance_api = BinanceApi()
        self.collection_name = "cached_candles"
        self.symbols_crud = SymbolsCrud()
        # Get logger and ensure it uses the root logger's configuration
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)  # Ensure it respects the basicConfig level

    def get_or_cache_klines(
        self,
        symbol: str,
        interval: BinanceKlineIntervals = BinanceKlineIntervals.one_day,
        limit: int = 500,
    ):
        """
        Ensure the candles collection exists as a timeseries collection with proper indexing
        If force_recreate is True, drops and recreates the collection
        """
        # Try to find klines in MongoDB
        query = {"symbol": symbol, "interval": interval.value}
        cached = list(
            self.db[self.collection_name].find(query).limit(limit).sort("timestamp", 1)
        )
        if len(cached) > 0:
            self.logger.info(
                f"Returning {len(cached)} cached klines for {symbol} {interval.value}"
            )
            # Convert MongoDB docs to Binance format if needed
            return [
                [
                    doc["open_time"],
                    doc["open"],
                    doc["high"],
                    doc["low"],
                    doc["close"],
                    doc["volume"],
                    doc["close_time"],
                ]
                for doc in cached
            ]
        else:
            self.db.drop_collection(self.collection_name)
            self.db.create_collection(
                self.collection_name,
                timeseries={
                    "timeField": "timestamp",
                    "metaField": "symbol",
                    "granularity": "hours",
                },
                expireAfterSeconds=24 * 3600,  # 1 day
            )
            self.logger.info(
                f"✅ Created timeseries collection: {self.collection_name}"
            )
            # Not found, fetch from Binance
            klines = self.binance_api.get_raw_klines(symbol=symbol, interval=interval)
            if klines:
                # Store in MongoDB
                docs = []
                for k in klines:
                    docs.append(
                        {
                            "symbol": symbol,
                            "interval": interval.value,
                            "open_time": k[0],
                            "open": k[1],
                            "high": k[2],
                            "low": k[3],
                            "close": k[4],
                            "volume": k[5],
                            "close_time": k[6],
                            "timestamp": datetime.fromtimestamp(
                                k[0] / 1000, tz=timezone.utc
                            ),
                        }
                    )
                if docs:
                    self.db[self.collection_name].insert_many(docs)

        cached = list(
            self.db[self.collection_name].find(query).limit(limit).sort("timestamp", 1)
        )
        return cached

    def get_btc_correlation(self, asset_symbol: str):
        """
        Get BTC correlation data for 1 day interval
        """
        asset_data = self.binance_api.get_raw_klines(
            symbol=asset_symbol, interval=BinanceKlineIntervals.one_day
        )

        btc_data = self.get_or_cache_klines(
            symbol="BTCUSDC", interval=BinanceKlineIntervals.one_day
        )

        # Format asset_data DataFrame columns to match Binance API kline data
        asset_df = DataFrame(asset_data)
        btc_df = DataFrame(btc_data)

        # Binance API kline format: [open_time, open, high, low, close, volume, close_time, ...]
        if len(asset_df.columns) >= 7:
            asset_df.columns = [
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
            ] + [f"col_{i}" for i in range(7, len(asset_df.columns))]

        if len(btc_df.columns) >= 7:
            btc_df.columns = [
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
            ] + [f"col_{i}" for i in range(7, len(btc_df.columns))]

        # Ensure close columns are numeric
        if "close" in asset_df.columns and "close" in btc_df.columns:
            asset_df["close"] = pd.to_numeric(asset_df["close"], errors="coerce")
            btc_df["close"] = pd.to_numeric(btc_df["close"], errors="coerce")

            p_correlation = asset_df["close"].corr(btc_df["close"], method="pearson")

            # Use cached call (default 1 hour). For 30 hours, pass ttl_seconds=30*3600
            price_perct = self.binance_api.ticker_24_last_price_cached(ttl_seconds=3600)

            return round_numbers(p_correlation), round_numbers(price_perct)
        else:
            return 0, 0
