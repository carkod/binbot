from pydantic import BaseModel
from pymongo import DESCENDING, ReturnDocument

from apis import BinbotApi
from database.mongodb.db import Database, setup_kafka_db, setup_db


class CandlestickItemRequest(BaseModel):
    data: list[list]
    symbol: str
    interval: str  # See EnumDefitions
    limit: int = 600
    offset: int = 0


class CandlestickParams(BaseModel):
    symbol: str
    interval: str  # See EnumDefinitions
    limit: int = 600
    startTime: float | None = (
        None  # starTime and endTime must be camel cased for the API
    )
    endTime: float | None = None


class KlinesSchema(Database):
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
