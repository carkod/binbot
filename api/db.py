import os
from pymongo import MongoClient
from tools.enum_definitions import Status


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
    _db = setup_db()
        

    # def get_autotrade_settings(self):
    #     return self._db.research_controller.find_one({"_id": "settings"})

    # def get_test_autotrade_settings(self):
    #     return self._db.research_controller.find_one({"_id": "test_autotrade_settings"})

    # def get_active_bots(self):
    #     bots = list(self._db.bots.distinct("pair", {"status": "active"}))
    #     return bots

    # def get_active_paper_trading_bots(self):
    #     bots = list(self._db.paper_trading.distinct("pair", {"status": "active"}))
    #     return bots
