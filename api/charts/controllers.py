from datetime import datetime
from pymongo import DESCENDING
from database.autotrade_crud import AutotradeCrud
from charts.models import MarketDominationSeriesStore, AdrSeriesDb
from apis import BinbotApi
from database.db import Database, setup_kafka_db
from pandas import DataFrame
from tools.enum_definitions import BinanceKlineIntervals
from tools.round_numbers import round_numbers
from database.symbols_crud import SymbolsCrud


class Candlestick(Database):
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """

    def __init__(self) -> None:
        self.db = setup_kafka_db()

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
                st_dt = datetime.fromtimestamp(start_time / 1000)
                query.append({"$match": {"_id.time": {"$gte": st_dt}}})

            if int(end_time) > 0:
                et_dt = datetime.fromtimestamp(end_time / 1000)
                query.append({"$match": {"_id.time": {"$lte": et_dt}}})

            query.append({"$sort": {"_id.time": -1}})
            query.append({"$limit": limit})
            query.append({"$skip": offset})

            result = self.db.kline.aggregate(query)
        data = list(result)
        return data


class MarketDominationController(Database, BinbotApi):
    """
    CRUD operations for market domination
    """

    def __init__(self) -> None:
        super().__init__()
        self.collection = self.kafka_db.market_domination
        self.autotrade_db = AutotradeCrud()
        self.autotrade_settings = self.autotrade_db.get_settings()
        self.symbols_crud = SymbolsCrud()

    def store_market_domination(self):
        """
        Store ticker 24 data every 30 min
        and calculate price change proportion
        This is how to construct market domination data

        The reason is to reduce weight, so as not to be banned by API
        """
        get_ticker_data = self.ticker_24()
        coin_data = []

        # ADR data ingestion
        advancers = 0
        decliners = 0
        adr = []
        total_volume = 0.0

        for item in get_ticker_data:
            if (
                item["symbol"].endswith(self.autotrade_settings.fiat)
                and float(item["lastPrice"]) > 0
            ):
                model_data = MarketDominationSeriesStore(
                    timestamp=datetime.fromtimestamp(
                        float(item["closeTime"]) / 1000
                    ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    time=datetime.fromtimestamp(
                        float(item["closeTime"]) / 1000
                    ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    symbol=item["symbol"],
                    priceChangePercent=float(item["priceChangePercent"]),
                    price=float(item["lastPrice"]),
                    volume=float(item["volume"]),
                )
                data = model_data.model_dump()
                coin_data.append(data)

                # ADR data ingestion starts here
                price_change_percent = float(item["priceChangePercent"])

                if price_change_percent > 0:
                    advancers += 1
                elif price_change_percent < 0:
                    decliners += 1

                total_volume += float(item["volume"])

                if advancers > 0 and decliners > 0:
                    adr_ratio = (advancers - decliners) / (advancers + decliners)
                    adr.append(adr_ratio)

        response = self.collection.insert_many(coin_data)

        # Store ADR data
        if advancers > 0 or decliners > 0:
            adr_data = AdrSeriesDb(
                timestamp=datetime.fromtimestamp(
                    int(float(get_ticker_data[-1]["closeTime"]) / 1000)
                ),
                advancers=advancers,
                decliners=decliners,
                adr=round_numbers(adr[-1]) if adr else 0.0,
                total_volume=total_volume,
            )
            self.kafka_db.adr.insert_one(adr_data.model_dump())

        return response

    def get_market_domination(self, size=7):
        """
        Get gainers vs losers historical data

        Args:
            size (int, optional): Number of data points to retrieve. Defaults to 7 (1 week).
        Returns:
            dict: A dictionary containing the market domination data, including gainers and losers counts, percentages, and dates.
        """
        result = self.collection.aggregate(
            [
                {
                    "$group": {
                        "_id": {
                            "time": {
                                "$dateTrunc": {
                                    "date": "$timestamp",
                                    "unit": "minute",
                                    "binSize": 60,
                                },
                            },
                        },
                        "data": {"$push": "$$ROOT"},
                    }
                },
                {"$sort": {"_id.time": DESCENDING}},
                {"$project": {"time": "$_id.time", "data": 1, "_id": 0}},
                {"$limit": size},
            ]
        )
        return list(result)

    def get_adrs(self, size=7, window=3):
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
            {"$addFields": {"timestamp_dt": {"$toDate": "$_id"}}},
            {"$sort": {"timestamp_dt": 1}},
            {
                "$setWindowFields": {
                    "sortBy": {"timestamp_dt": 1},
                    "output": {
                        "adr_ma": {
                            "$avg": "$adr",
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
                    "adr_ma": 1,
                    "advancers": 1,
                    "decliners": 1,
                    "total_volume": 1,
                    "adr": 1,
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
        ]
        results = list(self.kafka_db.adr.aggregate(pipeline))
        filtered = [doc for doc in results if doc.get("adr_ma") is not None][:size]
        return filtered

    def top_gainers(self):
        """
        Get market top gainers of the day

        ATTENTION - This is a very heavy weight operation
        ticker_24() retrieves all tokens
        """
        fiat = self.autotrade_db.get_fiat()
        ticket_data = self.ticker_24()

        fiat_market_data = sorted(
            (
                item
                for item in ticket_data
                if item["symbol"].endswith(fiat)
                and float(item["priceChangePercent"]) > 0
            ),
            key=lambda x: x["priceChangePercent"],
            reverse=True,
        )
        return fiat_market_data[:10]


class BtcCorrelation(Database, BinbotApi):
    """
    CRUD operations for BTC correlation
    """

    def __init__(self) -> None:
        super().__init__()
        self.collection = Candlestick()

    def get_btc_correlation(self, asset_symbol: str):
        """
        Get BTC correlation data
        for 1 day interval
        """
        asset_data = self.collection.raw_klines(
            symbol=asset_symbol, interval=BinanceKlineIntervals.one_day
        )
        btc_data = self.collection.raw_klines(
            symbol="BTCUSDC", interval=BinanceKlineIntervals.one_day
        )
        if len(asset_data) == 0 or len(btc_data) == 0:
            return None
        asset_df = DataFrame(asset_data)
        btc_df = DataFrame(btc_data)
        p_correlation = asset_df["close"].corr(btc_df["close"], method="pearson")
        return round_numbers(p_correlation)
