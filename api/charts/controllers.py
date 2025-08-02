import re
import logging
from datetime import datetime, timezone
from pymongo import DESCENDING
from database.autotrade_crud import AutotradeCrud
from charts.models import AdrSeriesDb
from apis import BinanceApi
from database.db import Database, setup_kafka_db
from pandas import DataFrame
from tools.enum_definitions import BinanceKlineIntervals
from database.symbols_crud import SymbolsCrud
from tools.round_numbers import round_numbers
from database.paper_trading_crud import PaperTradingTableCrud
from database.bot_crud import BotTableCrud


class Candlestick(Database):
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """

    def __init__(self) -> None:
        super().__init__()
        self.db = setup_kafka_db()
        self.binance_api = BinanceApi()

    def build_query(self, interval: BinanceKlineIntervals):
        bin_size = interval.bin_size()
        unit = interval.unit()
        group_stage = {
            "$group": {
                "_id": {
                    "time": {
                        "$dateTrunc": {
                            "date": "$close_time",
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
        returns klines ordered by close_time, from oldest to newest

        Returns:
            list: 15m Klines
        """
        query = self.db.kline.find(
            {"symbol": symbol},
            limit=limit,
            skip=offset,
            sort=[("_id", DESCENDING)],
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
        returns klines ordered by close_time, from oldest to newest

        Returns:
            list: 15m Klines
        """
        if interval == BinanceKlineIntervals.five_minutes:
            result = self.db.kline.find(
                {"symbol": symbol},
                {
                    "projection": {
                        "candle_closed": "0",
                        "_id": "0",
                    }
                },
                limit=limit,
                skip=offset,
                sort=[("_id", DESCENDING)],
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

            result = self.db.kline.aggregate(query)
        data = list(result)
        return data

    def get_btc_correlation(self, asset_symbol: str):
        """
        Get BTC correlation data
        for 1 day interval
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

    def get_klines(
        self,
        symbol,
        interval: BinanceKlineIntervals = BinanceKlineIntervals.one_minute,
        limit=200,
        offset=0,
        start_time=0,
        end_time=0,
    ) -> list[list]:
        """
        Query klines directly from MongoDB and return in Binance API format as array of arrays.
        Data is stored as 1-minute intervals and aggregated to requested interval.

        Returns:
            list[list]: Klines in simplified Binance API format:
            [
                [
                    open_time,      // Open time (timestamp)
                    open,           // Open price
                    high,           // High price
                    low,            // Low price
                    close,          // Close price
                    volume,         // Volume
                    close_time      // Close time (timestamp)
                ]
            ]
        """
        if interval == BinanceKlineIntervals.one_minute:
            # Direct query for 1-minute data (no aggregation needed)
            pipeline = [
                {"$match": {"symbol": symbol}},
                {"$sort": {"close_time": -1}},
                {"$skip": offset},
                {"$limit": limit},
                {"$sort": {"close_time": 1}},
                {
                    "$project": {
                        "_id": 0,
                        "kline": [
                            {"$toLong": "$open_time"},
                            {"$toString": "$open"},
                            {"$toString": "$high"},
                            {"$toString": "$low"},
                            {"$toString": "$close"},
                            {"$toString": "$volume"},
                            {"$toLong": "$close_time"},
                        ],
                    }
                },
            ]
        else:
            # Aggregated query for other intervals (5m, 15m, 1h, etc.)
            bin_size = interval.bin_size()
            unit = interval.unit()

            pipeline = [
                {"$match": {"symbol": symbol}},
            ]

            # Add time range filters if provided (convert milliseconds to datetime for comparison)
            if int(start_time) > 0:
                start_dt = datetime.fromtimestamp(
                    int(start_time) / 1000, tz=timezone.utc
                )
                pipeline.append({"$match": {"close_time": {"$gte": start_dt}}})

            if int(end_time) > 0:
                end_dt = datetime.fromtimestamp(int(end_time) / 1000, tz=timezone.utc)
                pipeline.append({"$match": {"close_time": {"$lte": end_dt}}})

            # Group stage for aggregation using datetime timestamps
            pipeline.extend(
                [
                    {
                        "$group": {
                            "_id": {
                                "time": {
                                    "$dateTrunc": {
                                        "date": "$close_time",
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
                    {"$sort": {"close_time": -1}},
                    {"$skip": offset},
                    {"$limit": limit},
                    {"$sort": {"close_time": 1}},
                    {
                        "$project": {
                            "_id": 0,
                            "kline": [
                                {"$toLong": "$_id.time"},
                                {"$toString": "$open"},
                                {"$toString": "$high"},
                                {"$toString": "$low"},
                                {"$toString": "$close"},
                                {"$toString": "$volume"},
                                {"$toLong": "$close_time"},
                            ],
                        }
                    },
                ]
            )

        # Execute the aggregation pipeline
        result = self.db.kline.aggregate(pipeline)
        data = list(result)

        # Extract the kline arrays from the documents
        # return [doc["kline"] for doc in data]
        return data

    def check_sync_with_binance(self, symbol: str) -> bool:
        """
        Check if the second-to-last kline matches Binance API
        We check the second-to-last because the last one is being updated by websockets
        Returns True if in sync, False if needs refresh
        """
        try:
            # Get our second-to-last kline (skip the last one as it's being updated)
            local_query = self.db.kline.find(
                {"symbol": symbol},
                {"_id": 0},
                limit=2,
                sort=[("close_time", DESCENDING)],  # close_time is now datetime
            )
            local_klines = list(local_query)

            if len(local_klines) < 2:
                logging.info(f"Not enough local data for {symbol}, sync check failed")
                return False

            # Get the second-to-last kline (index 1)
            local_second_last = local_klines[1]

            # Fetch last 2 klines from Binance (1-minute interval to match stored data)
            binance_klines = self.binance_api.get_raw_klines(
                symbol=symbol, limit=2, interval=BinanceKlineIntervals.one_minute.value
            )

            if not binance_klines or len(binance_klines) < 2:
                logging.warning(
                    f"Failed to fetch comparison data from Binance for {symbol}"
                )
                return False

            # Get Binance second-to-last kline (index 1, since they're ordered newest first)
            binance_second_last = binance_klines[1]

            # Compare key values: close_time, close_price, volume
            # Convert datetime to milliseconds for comparison
            local_close_time = int(local_second_last["close_time"].timestamp() * 1000)
            local_close_price = float(local_second_last["close"])
            local_volume = float(local_second_last["volume"])

            binance_close_time = int(binance_second_last[6])  # close_time
            binance_close_price = float(binance_second_last[4])  # close
            binance_volume = float(binance_second_last[5])  # volume

            # Check if they match (with small tolerance for floating point)
            time_match = local_close_time == binance_close_time
            price_match = abs(local_close_price - binance_close_price) < 0.0000001
            volume_match = abs(local_volume - binance_volume) < 0.0000001

            is_synced = time_match and price_match and volume_match

            return is_synced

        except Exception as e:
            logging.error(f"Error checking sync for {symbol}: {e}")
            return False

    def refresh_data_from_binance(self, symbol: str, limit: int = 500):
        """
        Delete existing data and fetch fresh data from Binance API
        This ensures data consistency and eliminates timestamp/pricing discrepancies
        """
        is_synced = self.check_sync_with_binance(symbol=symbol)

        if is_synced:
            return False

        self.db.kline.delete_many({"symbol": symbol})

        # Fetch fresh data from Binance
        raw_klines = self.binance_api.get_raw_klines(
            symbol=symbol, limit=limit, interval=BinanceKlineIntervals.one_minute.value
        )

        if not raw_klines:
            logging.warning(f"No data received from Binance for {symbol}")
            return

        # Prepare documents for bulk insert - use raw dict to avoid Pydantic validation issues
        kline_docs = []
        for k in raw_klines:
            if len(k) < 7:
                continue

            kline_doc = {
                "symbol": symbol,
                "end_time": datetime.fromtimestamp(int(k[6]) / 1000, tz=timezone.utc),
                "open_time": datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc),
                "close_time": datetime.fromtimestamp(int(k[6]) / 1000, tz=timezone.utc),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "candle_closed": True,
                "interval": BinanceKlineIntervals.one_minute.value,
            }

            kline_docs.append(kline_doc)

        if kline_docs:
            self.db.kline.insert_many(kline_docs)
            return True

class MarketDominationController(Database):
    """
    CRUD operations for market domination
    """

    def __init__(self) -> None:
        super().__init__()
        self.autotrade_db = AutotradeCrud()
        self.autotrade_settings = self.autotrade_db.get_settings()
        self.symbols_crud = SymbolsCrud()
        self.binance_api = BinanceApi()

    def ingest_adp_data(self):
        """
        Store ticker 24 data every 30 min
        and calculate price change proportion
        This is how to construct market domination data

        The reason is to reduce weight, so as not to be banned by API
        """
        get_ticker_data = self.binance_api.ticker_24()

        # ADR data ingestion
        advancers = 0
        decliners = 0
        total_volume = 0.0

        for item in get_ticker_data:
            if (
                item["symbol"].endswith(self.autotrade_settings.fiat)
                and float(item["lastPrice"]) > 0
            ):
                # ADR data ingestion starts here
                price_change_percent = float(item["priceChangePercent"])

                if price_change_percent > 0:
                    advancers += 1
                elif price_change_percent < 0:
                    decliners += 1

                total_volume += float(item["volume"])

        # Store ADR data
        adr_data = AdrSeriesDb(
            timestamp=datetime.fromtimestamp(
                float(item["closeTime"]) / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            advancers=advancers,
            decliners=decliners,
            total_volume=total_volume,
        )
        response = self.kafka_db.advancers_decliners.insert_one(adr_data.model_dump())

        return response

    def get_adrs(self, size=7, window=3) -> dict | None:
        """
        Get ADRs historical data with moving average of 'adr', using ObjectId _id for date.

        Args:
            size (int, optional): Number of data points to retrieve. Defaults to 7 (1 week).
            window (int, optional): Window size for moving average. Defaults to 3.
        Returns:
            list: A list of ADR data points with moving average.
        """
        fetch_size = size + window - 1
        pipeline = [
            {"$addFields": {"timestamp_dt": "$timestamp"}},
            {"$sort": {"timestamp_dt": 1}},
            {  # Compute adp before window function
                "$addFields": {
                    "adp": {
                        "$cond": [
                            {"$ne": [{"$add": ["$advancers", "$decliners"]}, 0]},
                            {
                                "$divide": [
                                    {"$subtract": ["$advancers", "$decliners"]},
                                    {"$add": ["$advancers", "$decliners"]},
                                ]
                            },
                            None,
                        ]
                    }
                }
            },
            {
                "$setWindowFields": {
                    "sortBy": {"timestamp_dt": 1},
                    "output": {
                        "adp_ma": {
                            "$avg": "$adp",
                            "window": {"documents": [-(window - 1), 0]},
                        }
                    },
                }
            },
            {"$sort": {"timestamp_dt": -1}},
            {"$limit": fetch_size},
            {
                "$project": {
                    "_id": 0,
                    "timestamp": "$timestamp_dt",
                    "adp_ma": 1,
                    "advancers": 1,
                    "decliners": 1,
                    "total_volume": 1,
                    "adp": 1,
                }
            },
            {
                "$addFields": {
                    "timestamp": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:%M:%S",
                            "date": "$timestamp",
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "timestamp": {"$push": "$timestamp"},
                    "adp_ma": {"$push": "$adp_ma"},
                    "advancers": {"$push": "$advancers"},
                    "decliners": {"$push": "$decliners"},
                    "total_volume": {"$push": "$total_volume"},
                    "adp": {"$push": "$adp"},
                }
            },
            {"$project": {"_id": 0}},
        ]
        results = self.kafka_db.advancers_decliners.aggregate(pipeline)
        data = list(results)
        if len(data) > 0:
            return data[0]
        return None

    def gainers_losers(self):
        """
        Get market top gainers of the day

        ATTENTION - This is a very heavy weight operation
        ticker_24() retrieves all tokens
        """
        fiat = self.autotrade_db.get_fiat()
        ticker_data = self.binance_api.ticker_24()

        gainers = sorted(
            [
                item
                for item in ticker_data
                if float(item["priceChangePercent"]) > 0
                and item["symbol"].endswith(fiat)
            ],
            key=lambda x: float(x["priceChangePercent"]),
            reverse=True,
        )

        losers = sorted(
            [
                item
                for item in ticker_data
                if float(item["priceChangePercent"]) < 0
                and item["symbol"].endswith(fiat)
            ],
            key=lambda x: float(x["priceChangePercent"]),
        )

        return gainers[:10], losers[:10]

    def algo_performance(self, paper_trading: bool = False) -> dict:
        """
        Get algorithm performance data
        from bots in the last month

        1. Get bots
        2. Parse names
        3. Do an aggregation of all profits and return net profit
        """
        algo_performance: dict = {}

        if paper_trading:
            bots_crud: PaperTradingTableCrud | BotTableCrud = PaperTradingTableCrud()

        else:
            bots_crud = BotTableCrud()

        bots = bots_crud.get()
        if not bots:
            return algo_performance
        else:
            for bot in bots:
                match_name = re.match(
                    r"^(.*?)(?=_[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2})", bot.name
                )
                if match_name:
                    key = match_name.group(1).lower()
                    if key not in algo_performance:
                        algo_performance[key] = {"net_profit": 0.0, "bots_count": 0}

                    if bot.deal.closing_price > 0:
                        algo_performance[key]["net_profit"] += round_numbers(
                            (bot.deal.closing_price - bot.deal.opening_price)
                            / bot.deal.closing_price
                        )

                    algo_performance[key]["bots_count"] += 1

        return algo_performance
