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
from database.paper_trading_crud import PaperTradingTableCrud
from database.bot_crud import BotTableCrud
import re


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

        # Store ADR data
        adr_data = AdrSeriesDb(
            timestamp=datetime.fromtimestamp(float(item["closeTime"]) / 1000).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )[:-3],
            advancers=advancers,
            decliners=decliners,
            total_volume=total_volume,
        )
        self.kafka_db.advancers_decliners.insert_one(adr_data.model_dump())
        response = self.collection.insert_many(coin_data)

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
