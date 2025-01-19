import logging
import json
from apis import BinanceApi
from streaming.socket_client import SpotWebsocketStreamClient
from database.db import Database
from database.bot_crud import BotTableCrud
from database.utils import independent_session


class UserDataStreaming(Database, BinanceApi):
    def __init__(self) -> None:
        self.streaming_db = self._db
        self.session = independent_session()
        self.bot_controller = BotTableCrud(session=self.session)
        pass

    def on_error(self, socket, error):
        logging.error(f"User data streaming error: {error}")
        pass

    def update_order_data(self, result):
        """
        Keep order data up to date

        When buy_order or sell_order is executed, they are often in
        status NEW, and it takes time to update to FILLED.
        This keeps order data up to date as they are executed
        throught the executionReport websocket

        Paper trading does not update orders. Orders are simulated.

        Args:
            result (dict): executionReport websocket result
            db_collection (str, optional): Defaults to "bots".

        """

        initial_order = self.bot_controller.get_order(order_id=int(result["i"]))

        if float(result["p"]) > 0:
            price = float(result["p"])
        else:
            price = float(result["L"])

        initial_order.order_id = int(result["i"])
        initial_order.status = result["X"]
        initial_order.qty = float(result["q"])
        initial_order.order_side = result["S"]
        initial_order.order_type = result["o"]
        initial_order.timestamp = result["T"]
        initial_order.pair = result["s"]
        initial_order.time_in_force = result["f"]
        initial_order.price = price

        order_result = self.bot_controller.update_order(
            order=initial_order, commission=float(result["n"])
        )

        return order_result

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
                self.update_order_data(res)
                return

            elif "outboundAccountPosition" in res["e"]:
                logging.info(f'Assets changed {res["e"]}')
            elif "balanceUpdate" in res["e"]:
                logging.info(f'Funds transferred {res["e"]}')
