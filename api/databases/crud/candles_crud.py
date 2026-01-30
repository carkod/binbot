import logging
from databases.db import setup_kafka_db
from pybinbot import BinanceKlineIntervals, BinanceApi
from databases.crud.symbols_crud import SymbolsCrud
from datetime import datetime, timezone
from pymongo.errors import OperationFailure
from tools.config import Config


class CandlesCrud:
    """
    CRUD operations for candles collection using timeseries with 1-month TTL
    Stores data in millisecond timestamps format for better performance
    """

    def __init__(self) -> None:
        super().__init__()
        self.db = setup_kafka_db()
        self.config = Config()
        self.binance_api = BinanceApi(
            key=self.config.binance_key, secret=self.config.binance_secret
        )
        self.collection_name = "cached_candles"
        self.symbols_crud = SymbolsCrud()
        # Get logger and ensure it uses the root logger's configuration
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)  # Ensure it respects the basicConfig level

    def _ingest_klines(self, symbol: str, interval: BinanceKlineIntervals) -> None:
        """
        Ingest klines into the database.
        """
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
            f"✅ Created timeseries collection: {self.collection_name} for {symbol}"
        )
        # Not found, fetch from Binance
        klines = self.binance_api.get_ui_klines(symbol=symbol, interval=interval.value)
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
        try:
            cached = list(
                self.db[self.collection_name]
                .find(query)
                .limit(limit)
                .sort("timestamp", 1)
            )
        except OperationFailure as e:
            self.logger.error(f"Error fetching cached klines: {e}")
            self._ingest_klines(symbol, interval)

        if len(cached) == 0:
            self.logger.info(
                f"Returning {len(cached)} cached klines for {symbol} {interval.value}"
            )
            self._ingest_klines(symbol, interval)

        cached = list(
            self.db[self.collection_name].find(query).limit(limit).sort("timestamp", 1)
        )
        return cached
