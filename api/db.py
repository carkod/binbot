import os
from pymongo import MongoClient, ReturnDocument
from bots.schemas import BotSchema
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
    """
    The whole objective of having this class is to provide
    a single point of entry to the database.
    Therefore, always initialize database instance

    Methods in this should only be helpers
    that can be independently triggered, where
    only dependency is the _db instance
    """
    _db = setup_db()

    def save_bot_streaming(self, active_bot: BotSchema, db_collection_name: str="bots"):
        """
        MongoDB query to save bot using Pydantic

        This function differs from usual save query in that
        it returns the saved bot, thus called streaming, it's
        specifically for streaming saves

        Returns:
            dict: The saved bot
        """

        bot = BotSchema.model_dump(active_bot)
        if "_id" in bot:
            bot.pop("_id")

        response = self._db[db_collection_name].find_one_and_update(
            {"id": active_bot.id},
            {
                "$set": bot,
            },
            return_document=ReturnDocument.AFTER,
        )

        active_bot = BotSchema(**response)
        return active_bot

    def update_deal_logs(self, msg, active_bot: BotSchema, db_collection_name: str="bots"):
        """
        Use this function if independently updating Event logs (deal.errors list)
        especially useful if a certain operation might fail in an exception
        and the error needs to be stored in the logs

        However, if save_bot_streaming is used later,
        and there is almost no chance of failure,
        best to this.active_bot.errors.append(str(msg)) so we can save
        some DB calls.
        """
        result = self._db[db_collection_name].find_one_and_update(
            {"id": active_bot.id},
            {"$push": {"errors": str(msg)}},
            return_document=ReturnDocument.AFTER,
        )
        active_bot.errors = result["errors"]
        return result

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
