import logging
from datetime import datetime, timezone
from time import sleep
from pymongo import DESCENDING
from apis import BinanceApi
from databases.db import setup_kafka_db
from pandas import DataFrame
from tools.enum_definitions import BinanceKlineIntervals
from tools.round_numbers import round_numbers
from databases.crud.symbols_crud import SymbolsCrud

# Configure logging to show INFO level messages
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
        self.collection_name = "candles"
        self.symbols_crud = SymbolsCrud()
        # Get logger and ensure it uses the root logger's configuration
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)  # Ensure it respects the basicConfig level
        self.ensure_collection_setup()

    def ensure_collection_setup(self, force_recreate=False):
        """
        Ensure the candles collection exists as a timeseries collection with proper indexing
        If force_recreate is True, drops and recreates the collection
        """

        if (
            force_recreate
            or self.collection_name not in self.db.list_collection_names()
        ):
            # Drop existing collection if it exists and we're forcing recreate
            if (
                force_recreate
                and self.collection_name in self.db.list_collection_names()
            ):
                self.logger.info(
                    f"🗑️ Dropping existing collection {self.collection_name} for recreation"
                )
                self.db.drop_collection(self.collection_name)

            self.db.create_collection(
                self.collection_name,
                timeseries={
                    "timeField": "time",
                    "metaField": "symbol",
                    "granularity": "minutes",
                },
            )
            self.logger.info(
                f"✅ Created timeseries collection: {self.collection_name}"
            )

    def build_query(self, interval: BinanceKlineIntervals):
        bin_size = interval.bin_size()
        unit = interval.unit()
        group_stage = {
            "$group": {
                "_id": {
                    "time": {
                        "$dateTrunc": {
                            "date": "$time",
                            "unit": unit,
                            "binSize": bin_size,
                        },
                    },
                },
                "open": {"$first": "$open"},
                "close": {"$last": "$close"},
                "high": {"$max": "$high"},
                "low": {"$min": "$low"},
                "close_time": {"$last": "$close_time"},
                "open_time": {"$first": "$open_time"},
                "volume": {"$sum": "$volume"},
            }
        }
        return group_stage

    def get_timeseries(self, symbol, limit=200, offset=0):
        """
        Query specifically for display or analytics,
        returns klines ordered by time, from newest to oldest

        Returns:
            list: 15m Klines
        """
        query = self.db.candles.find(
            {"symbol": symbol},
            limit=limit,
            skip=offset,
            sort=[("time", 1)],
        )
        data = list(query)
        return data

    def raw_klines(
        self,
        symbol,
        interval: BinanceKlineIntervals = BinanceKlineIntervals.fifteen_minutes,
        limit=200,
        offset=0,
        start_time=0,
        end_time=0,
    ) -> list[dict]:
        """
        Query specifically for display or analytics,
        returns klines ordered by time,
         from newest to oldest

        Returns:
            list: 15m Klines
        """
        if interval == BinanceKlineIntervals.fifteen_minutes:
            result = self.db.candles.find(
                {"symbol": symbol},
                {"_id": 0},  # Fixed: removed $ prefix and simplified projection
                limit=limit,
                skip=offset,
                sort=[("time", DESCENDING)],
            )
        else:
            query = []
            group_stage = self.build_query(interval)
            match_stage = {"symbol": symbol}

            query.append({"$match": match_stage})
            query.append(group_stage)

            if int(start_time) > 0:
                st_dt = datetime.fromtimestamp(start_time / 1000, tz=timezone.utc)
                query.append({"$match": {"_id.time": {"$gte": st_dt}}})

            if int(end_time) > 0:
                et_dt = datetime.fromtimestamp(end_time / 1000, tz=timezone.utc)
                query.append({"$match": {"_id.time": {"$lte": et_dt}}})

            query.append({"$sort": {"_id.time": -1}})
            query.append({"$limit": limit})
            query.append({"$skip": offset})

            result = self.db.candles.aggregate(query)
        data = list(result)
        return data

    def get_btc_correlation(self, asset_symbol: str):
        """
        Get BTC correlation data for 1 day interval
        """
        asset_data = self.raw_klines(
            symbol=asset_symbol, interval=BinanceKlineIntervals.one_day
        )
        btc_data = self.raw_klines(
            symbol="BTCUSDC", interval=BinanceKlineIntervals.one_day
        )
        if len(asset_data) == 0 or len(btc_data) == 0:
            return None
        asset_df = DataFrame(asset_data)
        btc_df = DataFrame(btc_data)
        p_correlation = asset_df["close"].corr(btc_df["close"], method="pearson")
        return round_numbers(p_correlation)

    def get_candles(
        self,
        symbol,
        interval: BinanceKlineIntervals = BinanceKlineIntervals.fifteen_minutes,
        limit=200,
        offset=0,
        start_time=0,
        end_time=0,
    ) -> list[list]:
        """
        Query klines directly from MongoDB and return in Binance API format as array of arrays.
        Data is stored as 15-minute intervals and aggregated to requested interval.
        Returns millisecond timestamps as integers for better compatibility.

        Returns:
            list[list]: Klines in simplified Binance API format:
            [
                [
                    open_time,      // Open time (millisecond timestamp)
                    open,           // Open price
                    high,           // High price
                    low,            // Low price
                    close,          // Close price
                    volume,         // Volume
                    close_time      // Close time (millisecond timestamp)
                ]
            ]
        """
        if interval == BinanceKlineIntervals.fifteen_minutes:
            # Direct query for 15-minute data (no aggregation needed)
            pipeline = [
                {"$match": {"symbol": symbol}},
                {"$sort": {"time": -1}},
                {"$skip": offset},
                {"$limit": limit},
                {"$sort": {"time": 1}},
                {
                    "$project": {
                        "_id": 0,
                        "kline": [
                            "$open_time",  # Already in milliseconds
                            {"$toString": "$open"},
                            {"$toString": "$high"},
                            {"$toString": "$low"},
                            {"$toString": "$close"},
                            {"$toString": "$volume"},
                            "$close_time",  # Already in milliseconds
                        ],
                    }
                },
            ]
        else:
            # Aggregated query for other intervals (30m, 1h, 4h, etc.)
            bin_size = interval.bin_size()
            unit = interval.unit()

            pipeline = [
                {"$match": {"symbol": symbol}},
            ]

            # Add time range filters if provided
            if int(start_time) > 0:
                start_dt = datetime.fromtimestamp(
                    int(start_time) / 1000, tz=timezone.utc
                )
                pipeline.append({"$match": {"time": {"$gte": start_dt}}})

            if int(end_time) > 0:
                end_dt = datetime.fromtimestamp(int(end_time) / 1000, tz=timezone.utc)
                pipeline.append({"$match": {"time": {"$lte": end_dt}}})

            # Group stage for aggregation using datetime timestamps
            pipeline.extend(
                [
                    {
                        "$group": {
                            "_id": {
                                "time": {
                                    "$dateTrunc": {
                                        "date": "$time",
                                        "unit": unit,
                                        "binSize": bin_size,
                                    },
                                },
                            },
                            "open": {"$first": "$open"},
                            "close": {"$last": "$close"},
                            "high": {"$max": "$high"},
                            "low": {"$min": "$low"},
                            "close_time": {"$last": "$close_time"},
                            "open_time": {"$first": "$open_time"},
                            "volume": {"$sum": "$volume"},
                        }
                    },
                    {"$sort": {"_id.time": -1}},
                    {"$skip": offset},
                    {"$limit": limit},
                    {"$sort": {"_id.time": 1}},
                    {
                        "$project": {
                            "_id": 0,
                            "kline": [
                                {
                                    "$toLong": {
                                        "$multiply": [{"$toLong": "$_id.time"}, 1]
                                    }
                                },  # Convert datetime to milliseconds
                                {"$toString": "$open"},
                                {"$toString": "$high"},
                                {"$toString": "$low"},
                                {"$toString": "$close"},
                                {"$toString": "$volume"},
                                "$close_time",  # Already in milliseconds
                            ],
                        }
                    },
                ]
            )

        # Execute the aggregation pipeline
        result = self.db.candles.aggregate(pipeline)
        data = list(result)

        # Extract the kline arrays from the documents
        return [doc["kline"] for doc in data]

    def check_sync_with_binance(self, symbol: str) -> bool:
        """
        Check if the time interval between recent klines is consistent with 15-minute intervals
        We check the gap between second-to-last and third-to-last klines
        Returns True if intervals are consistent, False if needs refresh
        """
        try:
            # Get our last 3 klines to check interval consistency
            local_query = self.db.candles.find(
                {"symbol": symbol},
                {"_id": 0, "close_time": 1},
                limit=3,
                sort=[("time", DESCENDING)],
            )
            local_klines = list(local_query)

            if len(local_klines) < 3:
                self.logger.info(
                    f"Not enough local data for {symbol}, sync check failed"
                )
                return False

            # Get the second-to-last and third-to-last klines
            second_last = local_klines[1]
            third_last = local_klines[2]

            # Extract close_time (in milliseconds)
            second_last_time = int(second_last["close_time"])
            third_last_time = int(third_last["close_time"])

            # Calculate the time difference in milliseconds
            time_diff_ms = second_last_time - third_last_time

            # Expected 15-minute interval in milliseconds (15 * 60 * 1000 = 900000)
            expected_interval_ms = 900000

            # Allow some tolerance (±30 seconds = ±30000 ms) for timing variations
            tolerance_ms = 30000

            # Check if the interval is within expected range
            is_valid_interval = abs(time_diff_ms - expected_interval_ms) <= tolerance_ms

            if not is_valid_interval:
                self.logger.warning(
                    f"Invalid interval detected for {symbol}: "
                    f"expected ~{expected_interval_ms}ms, got {time_diff_ms}ms"
                )

            return is_valid_interval

        except Exception as e:
            self.logger.error(f"Error checking sync for {symbol}: {e}")
            return False

    def refresh_data_from_binance(
        self, symbol: str, limit: int = 500, force_refresh: bool = False
    ):
        """
        Delete existing data and fetch fresh data from Binance API
        This ensures data consistency and eliminates timestamp/pricing discrepancies

        Args:
            symbol: Symbol to refresh
            limit: Number of klines to fetch
            force_refresh: If True, skips sync check and always refreshes
        """
        # Always force refresh if explicitly requested, otherwise check sync
        if not force_refresh:
            is_synced = self.check_sync_with_binance(symbol=symbol)
            if is_synced:
                return False

        # Delete existing data for this symbol
        delete_result = self.db.candles.delete_many({"symbol": symbol})
        if delete_result.deleted_count > 0:
            self.logger.info(
                f"🗑️ Deleted {delete_result.deleted_count} existing documents for {symbol}"
            )

        # Fetch fresh data from Binance
        raw_klines = self.binance_api.get_raw_klines(
            symbol=symbol,
            limit=limit,
            interval=BinanceKlineIntervals.fifteen_minutes.value,
        )

        if not raw_klines:
            self.logger.warning(f"No data received from Binance for {symbol}")
            return False

        # Prepare documents for bulk insert
        kline_docs = []
        for k in raw_klines:
            if len(k) < 7:
                continue

            kline_doc = {
                "symbol": symbol,
                "time": datetime.fromtimestamp(int(k[6]) / 1000, tz=timezone.utc),
                "open_time": int(k[0]),
                "close_time": int(k[6]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "candle_closed": True,
                "interval": BinanceKlineIntervals.fifteen_minutes.value,
            }

            kline_docs.append(kline_doc)

        if kline_docs:
            try:
                self.db.candles.insert_many(kline_docs)
                self.logger.info(
                    f"✅ Successfully bulk inserted {len(kline_docs)} candles for {symbol}"
                )
                return True

            except Exception as e:
                self.logger.error(f"❌ Failed to insert data for {symbol}: {e}")
                raise e

        return False

    def drop_collection_and_refresh_all(self, limit: int = 500):
        """
        Drop the candles collection and refresh data for all active symbols
        Implements rate limiting to avoid hitting Binance API weight limits

        Args:
            limit: Number of klines to fetch per symbol

        Returns:
            dict: Summary of the operation with success/failure counts
        """
        # Get all active symbols first
        active_symbols = self.symbols_crud.get_all(active=True)
        total_active_symbols = len(active_symbols)

        # Check if we already have data for all active symbols
        try:
            current_symbols = self.db.candles.distinct("symbol")
            symbols_count_in_collection = len(current_symbols)

            self.logger.info(
                f"📊 Found {symbols_count_in_collection} symbols in collection vs {total_active_symbols} active symbols"
            )

            # If we already have all symbols, skip refresh
            if symbols_count_in_collection >= total_active_symbols:
                self.logger.info(
                    f"✅ Collection already has data for {symbols_count_in_collection} symbols, "
                    f"which matches or exceeds {total_active_symbols} active symbols. Skipping drop and refresh."
                )
                return

        except Exception as e:
            self.logger.warning(
                f"⚠️ Could not check collection state: {e}, proceeding with refresh"
            )

        # Drop the entire candles collection
        self.logger.info("🗑️ Dropping candles collection...")
        self.db.drop_collection(self.collection_name)
        self.logger.info("✅ Collection dropped successfully")

        # Recreate the collection with proper settings
        self.ensure_collection_setup(force_recreate=True)

        # Process all active symbols
        total_symbols = len(active_symbols)
        self.logger.info(f"📊 Found {total_symbols} active symbols to process")
        count = 0
        successful_count = 0
        failed_count = 0

        for symbol_data in active_symbols:
            if not symbol_data.id:
                self.logger.warning(f"Symbol not found in data: {symbol_data.id}")
                failed_count += 1
                continue

            count += 1
            self.logger.info(
                f"🔄 Processing {symbol_data.id} ({count}/{total_symbols})"
            )

            try:
                self.refresh_data_from_binance(symbol_data.id, limit)
                successful_count += 1
            except Exception as e:
                failed_count += 1
                self.logger.error(f"❌ Failed to process {symbol_data.id}: {e}")

        self.logger.info(
            f"✅ Completed processing {count} symbols (Success: {successful_count}, Failed: {failed_count})"
        )

        # Log final collection count
        final_count = len(self.db.candles.distinct("symbol"))
        self.logger.info(f"📊 Final distinct symbols in collection: {final_count}")
        sleep(10)

        if final_count >= total_active_symbols:
            self.logger.info(
                f"✅ SUCCESS: All {total_active_symbols} active symbols are in collection"
            )
        else:
            self.logger.warning(
                f"⚠️ WARNING: Only {final_count}/{total_active_symbols} symbols in collection"
            )
