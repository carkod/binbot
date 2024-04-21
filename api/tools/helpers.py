from pymongo import ReturnDocument
from db import Database


class MongoDbHelpers(Database):

    def update_deal_logs(self, msg):
        """
        Use this function if independently updating Event logs (deal.errors list)
        especially useful if a certain operation might fail in an exception
        and the error needs to be stored in the logs

        However, if save_bot_streaming is used later,
        and there is almost no chance of failure,
        best to this.active_bot.errors.append(str(msg)) so we can save
        some DB calls.
        """
        result = self.db_collection.find_one_and_update(
            {"id": self.active_bot.id},
            {"$push": {"errors": str(msg)}},
            return_document=ReturnDocument.AFTER,
        )
        self.active_bot.errors = result["errors"]
        return result