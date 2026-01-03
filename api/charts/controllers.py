import re
from datetime import UTC, datetime

from pybinbot import round_numbers

from apis import BinanceApi
from charts.models import AdrSeriesDb
from databases.crud.autotrade_crud import AutotradeCrud
from databases.crud.bot_crud import BotTableCrud
from databases.crud.paper_trading_crud import PaperTradingTableCrud
from databases.crud.symbols_crud import SymbolsCrud
from databases.db import Database


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
        and calculate ADR + Strength Index
        """
        get_ticker_data = self.binance_api.ticker_24()

        advancers = 0
        decliners = 0
        total_volume = 0.0
        gains = []
        losses = []

        timestamp = None

        for item in get_ticker_data:
            if (
                item["symbol"].endswith(self.autotrade_settings.fiat)
                and float(item["lastPrice"]) > 0
            ):
                price_change_percent = float(item["priceChangePercent"])

                if price_change_percent > 0:
                    advancers += 1
                    gains.append(price_change_percent)
                elif price_change_percent < 0:
                    decliners += 1
                    losses.append(price_change_percent)

                total_volume += float(item["volume"])
                timestamp = datetime.fromtimestamp(
                    float(item["closeTime"]) / 1000, tz=UTC
                ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        avg_gain = sum(gains) / len(gains) if gains else 0.0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0

        gain_power = advancers * avg_gain
        loss_power = decliners * avg_loss

        if (gain_power + loss_power) > 0:
            strength_index = (gain_power - loss_power) / (gain_power + loss_power)
        else:
            strength_index = 0.0

        adr_data = AdrSeriesDb(
            timestamp=timestamp,
            advancers=advancers,
            decliners=decliners,
            total_volume=total_volume,
            strength_index=strength_index,
            avg_gain=avg_gain,
            avg_loss=avg_loss,
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
                    "strength_index": 1,
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
                    "strength_index": {"$push": "$strength_index"},
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
