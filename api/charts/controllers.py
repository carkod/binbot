from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import CollectionInvalid
from database.autotrade_crud import AutotradeCrud
from charts.models import MarketDominationSeriesStore
from apis import BinbotApi
from database.db import Database, setup_db, setup_kafka_db
from pandas import DataFrame


class KlinesSchema(Database):
    """
    Candlestick data CRUD operations
    """

    def __init__(self, pair, interval=None, limit=500) -> None:
        self._id = pair  # pair
        self.interval = interval
        self.limit = limit
        self.db = setup_db()

    def create(self, data):
        try:
            result = self.db.klines.insert_one({"_id": self._id, self.interval: data})
            return result
        except Exception as e:
            return e

    def replace_klines(self, data):
        try:
            result = self.db.klines.find_one_and_update(
                {"_id": self._id},
                {"$set": {self.interval: data}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            return result
        except Exception as e:
            return e

    def update_data(self, data, timestamp=None):
        """
        Function that specifically updates candlesticks from websockets
        Finds existence of candlesticks and then updates with new stream kline data or adds new data
        """
        new_data = data  # This is not existent data but stream data from API
        try:
            kline = self.db.klines.find_one({"_id": self._id})
            curr_ts = kline[self.interval][len(kline[self.interval]) - 1][0]
            if curr_ts == timestamp:
                # If found timestamp match - update
                self.db.klines.update_one(
                    {"_id": self._id},
                    {"$pop": {self.interval: 1}},
                )
                update_kline = self.db.klines.update_one(
                    {"_id": self._id},
                    {"$push": {self.interval: new_data}},
                )
            else:
                # If no timestamp match - push
                update_kline = self.db.klines.update_one(
                    {"_id": self._id},
                    {
                        "$push": {
                            self.interval: {
                                "$each": [new_data],
                            }
                        }
                    },
                )

            return update_kline
        except Exception as e:
            return e

    def delete_klines(self):
        result = self.db.klines.delete_one({"symbol": self._id})
        return result.acknowledged


class Candlestick(BinbotApi):
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """

    def __init__(self) -> None:
        self.db = setup_db()

    def get_timeseries(self, symbol, limit=200, offset=0):
        """
        Query specifically for display or analytics,
        returns klines ordered by close_time, from oldest to newest

        Returns:
            list: 15m Klines
        """
        kafka_db = setup_kafka_db()
        query = kafka_db.kline.find(
            {"symbol": symbol},
            {"_id": 0, "candle_closed": 0},
            limit=limit,
            skip=offset,
            sort=[("_id", DESCENDING)],
        )
        data = list(query)
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

    def mkdm_migration(self):
        """
        One time migration of market domination data from MongoDB ordinary db to MongoDB timeseries format

        1. Check if collection exists. If not, code will continue
        else it will raise an error and finish the task
        2. Migrate market domination data to time series format
        """
        try:
            self.kafka_db.create_collection(
                "market_domination",
                # 1 week worth of data
                expireAfterSeconds=604800,
                check_exists=True,
                timeseries={
                    "timeField": "timestamp",
                    "metaField": "symbol",
                    "granularity": "minutes",
                },
            )
        except CollectionInvalid:
            return

        # Start migration
        one_week_ago = datetime.now() - timedelta(weeks=1)
        one_week_ago_object_id = ObjectId.from_datetime(one_week_ago)

        data = self._db.market_domination.find(
            {"_id": {"$gte": one_week_ago_object_id}}
        )
        data_collection = list(data)
        formatted_data = []

        for item in data_collection:
            for ticker in item["data"]:
                if float(ticker["priceChangePercent"]) > 0:
                    store_data = MarketDominationSeriesStore(
                        timestamp=datetime.strptime(
                            item["time"], "%Y-%m-%d %H:%M:%S.%f"
                        ),
                        time=item["time"],
                        symbol=ticker["symbol"],
                        priceChangePercent=float(ticker["priceChangePercent"]),
                        price=float(ticker["price"]),
                        volume=float(ticker["volume"]),
                    )
                    md_data = store_data.model_dump()
                    formatted_data.append(md_data)

        self.collection.insert_many(formatted_data)

    def store_market_domination(self):
        """
        Store ticker 24 data every 30 min
        and calculate price change proportion
        This is how to construct market domination data

        The reason is to reduce weight, so as not to be banned by API
        """
        get_ticker_data = self.ticker_24()
        coin_data = []
        try:
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
        except Exception as e:
            print(e)

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
        TODO: wait for BTCUSDC data to populate by Binquant
        """
        asset_data = self.collection.get_timeseries(asset_symbol)
        btc_data = self.collection.get_timeseries("BTCUSDT")
        asset_df = DataFrame(asset_data, columns=["close"])
        btc_df = DataFrame(btc_data, columns=["close"])
        p_correlation = asset_df["close"].corr(btc_df["close"], method="pearson")
        return p_correlation
