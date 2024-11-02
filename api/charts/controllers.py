
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import DESCENDING, ReturnDocument
from charts.models import MarketDominationSeriesStore
from apis import BinbotApi
from database.mongodb.db import Database, setup_db, setup_kafka_db


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

    def mkdm_migration(self):
        """
        One time migration of market domination data from MongoDB ordinary db to MongoDB timeseries format
        """
        one_week_ago = datetime.now() - timedelta(weeks=1)
        one_week_ago_object_id = ObjectId.from_datetime(one_week_ago)

        data = self._db.market_domination.find({
            '_id': {'$gte': one_week_ago_object_id}
        })
        data_collection = list(data)
        formatted_data = []
        for item in data_collection:
            for ticker in item["data"]:
                formatted_data.append(MarketDominationSeriesStore(
                    time=item["time"],
                    symbol=ticker["symbol"],
                    priceChangePercent=float(ticker["priceChangePercent"]),
                    price=float(ticker["price"])
                    
                ))
        self.kafka_db.create_collection(
            "market_domination",
            capped=True,
            # 1 week worth of data
            max=336,
            expireAfterSeconds=604800,
            check_exists=True,
            timeseries={'time': 'timestamp'}
        )
        self.collection.create_index(
            [("time", DESCENDING)], unique=True
        )
        self.collection.create_index(
            [("symbol", DESCENDING)]
        )
        self.collection.insert_many(formatted_data)

    def store_market_domination(self):
        get_ticker_data = self.ticker_24()
        all_coins = []
        for item in get_ticker_data:
            if item["symbol"].endswith("USDC") and float(item["price"]) > 0:
                all_coins.append(
                    {
                        "symbol": item["symbol"],
                        "priceChangePercent": item["priceChangePercent"],
                        "volume": item["volume"],
                        "price": item["lastPrice"],
                    }
                )

        all_coins = sorted(
            all_coins, key=lambda item: float(item["priceChangePercent"]), reverse=True
        )
        current_time = datetime.now()
        response = self.collection.insert_one(
            {
                "time": current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "data": all_coins,
            }
        )
        return response

    def get_market_domination(self, size=7):
        """
        Get gainers vs losers historical data

        Args:
            size (int, optional): Number of data points to retrieve. Defaults to 7 (1 week).
        Returns:
            dict: A dictionary containing the market domination data, including gainers and losers counts, percentages, and dates.
        """
        query = {"$query": {}, "$orderby": {"_id": -1}}
        result = self.collection.find(query).limit(size)
        return list(result)
