import os
from pymongo import MongoClient


def setup_db():
    # Database
    mongo = MongoClient(
        host=os.getenv("MONGO_HOSTNAME"),
        port=int(os.getenv("MONGO_PORT")),
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD"),
    )
    db = mongo[os.getenv("MONGO_APP_DATABASE")]
    return db


class Database:
    def __init__(self):
        self._db = setup_db()

    def get_autotrade_settings(self):
        return self._db.research_controller.find_one({"_id": "settings"})

    def get_test_autotrade_settings(self):
        return self._db.research_controller.find_one({"_id": "test_autotrade_settings"})

    def get_active_bots(self):
        bots = list(self._db.bots.distinct("pair", {"status": "active"}))
        return bots

    def get_active_paper_trading_bots(self):
        bots = list(self._db.paper_trading.distinct("pair", {"status": "active"}))
        return bots

    def query_market_domination(self, size: int = 7):
        """
        Get market domination data and order by DESC _id,
        which means earliest data will be at the end of the list.
        """
        query = {"$query": {}, "$orderby": {"_id": -1}}
        result = self._db.market_domination.find(query).limit(size)
        return list(result)
