import os
from time import time
from bson import ObjectId
from pymongo import MongoClient, ReturnDocument
from tools.handle_error import encode_json
from deals.models import DealModel
from bots.schemas import BotSchema
from tools.enum_definitions import Status, AutotradeSettingsDocument


def get_mongo_client():
    client: MongoClient = MongoClient(
        host=os.getenv("MONGO_HOSTNAME"),
        port=int(os.getenv("MONGO_PORT", 2017)),
        authSource="admin",
        username=os.getenv("MONGO_AUTH_USERNAME"),
        password=os.getenv("MONGO_AUTH_PASSWORD"),
    )
    return client


def setup_db():
    # Database
    mongo = get_mongo_client()
    db = mongo[os.getenv("MONGO_APP_DATABASE")]
    return db


def setup_kafka_db():
    # Time series optimized database
    mongo = get_mongo_client()
    db = mongo[os.getenv("MONGO_KAFKA_DATABASE")]
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
    kafka_db = setup_kafka_db()

    def get_fiat_coin(self):
        document_id = AutotradeSettingsDocument.settings
        settings = self._db.research_controller.find_one({"_id": document_id})
        return settings["balance_to_use"]

    def save_bot_streaming(
        self, active_bot: BotSchema, db_collection_name: str = "bots"
    ) -> BotSchema:
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

        active_bot = BotSchema.model_validate(response)
        return active_bot

    def update_deal_logs(
        self, message, active_bot: BotSchema, db_collection_name: str = "bots"
    ):
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
            {"$push": {"errors": str(message)}},
            return_document=ReturnDocument.AFTER,
        )
        active_bot.errors = result["errors"]
        return result

    def create_new_bot_streaming(
        self, active_bot: BotSchema, db_collection_name: str = "bots"
    ):
        """
        Resets bot to initial state and saves it to DB

        This function differs from usual create_bot in that
        it needs to set strategy first (reversal)
        clear orders, deal and errors,
        which are not required in new bots,
        as they initialize with empty values
        """
        active_bot.id = str(ObjectId())
        active_bot.orders = []
        active_bot.errors = []
        active_bot.created_at = time() * 1000
        active_bot.updated_at = time() * 1000
        active_bot.status = Status.inactive
        active_bot.deal = DealModel()

        bot = encode_json(active_bot)
        self._db[db_collection_name].insert_one(bot)
        new_bot = self._db[db_collection_name].find_one({"id": bot["id"]})
        new_bot_class = BotSchema(**new_bot)

        return new_bot_class
