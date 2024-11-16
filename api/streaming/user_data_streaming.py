import logging
import json
from apis import BinanceApi
from streaming.socket_client import SpotWebsocketStreamClient
from database.db import Database


class UserDataStreaming(Database, BinanceApi):
    def __init__(self) -> None:
        self.streaming_db = self._db
        pass

    def on_error(self, socket, error):
        logging.error(f"User data streaming error: {error}")
        pass

    def update_order_data(self, result, db_collection: str = "bots"):
        """
        Keep order data up to date

        When buy_order or sell_order is executed, they are often in
        status NEW, and it takes time to update to FILLED.
        This keeps order data up to date as they are executed
        throught the executionReport websocket

        Args:
            result (dict): executionReport websocket result
            db_collection (str, optional): Defaults to "bots".

        """
        order_id = result["i"]
        update = {
            "$set": {
                "orders.$.status": result["X"],
                "orders.$.qty": result["q"],
                "orders.$.order_side": result["S"],
                "orders.$.order_type": result["o"],
                "orders.$.timestamp": result["T"],
            },
            "$inc": {"total_commission": float(result["n"])},
            "$push": {"errors": "Order status updated"},
        }
        if float(result["p"]) > 0:
            update["$set"]["orders.$.price"] = float(result["p"])
        else:
            update["$set"]["orders.$.price"] = float(result["L"])

        query = self.streaming_db[db_collection].update_one(
            {"orders": {"$elemMatch": {"order_id": order_id}}},
            update,
        )
        return query

    def get_user_data(self):
        listen_key = self.get_listen_key()
        self.user_data_client = SpotWebsocketStreamClient(
            on_message=self.on_user_data_message, on_error=self.on_error
        )
        self.user_data_client.user_data(
            listen_key=listen_key, action=SpotWebsocketStreamClient.subscribe
        )

    def on_user_data_message(self, socket, message):
        """
        Legacy, needs improvement
        """
        logging.info("Streaming user data")
        res = json.loads(message)

        if "e" in res:
            if "executionReport" in res["e"]:
                query = self.update_order_data(res)
                if query.raw_result["nModified"] == 0:
                    logging.debug(
                        f'No bot found with order client order id: {res["i"]}. Order status: {res["X"]}'
                    )
                return

            elif "outboundAccountPosition" in res["e"]:
                logging.info(f'Assets changed {res["e"]}')
            elif "balanceUpdate" in res["e"]:
                logging.info(f'Funds transferred {res["e"]}')
