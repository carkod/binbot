import logging
import json
import asyncio
from exchange_apis.binance import BinanceApi
from streaming.socket_client import AsyncSpotWebsocketStreamClient
from databases.db import Database
from databases.crud.bot_crud import BotTableCrud
from databases.utils import independent_session
from tools.logging_config import configure_logging

configure_logging(force=True)


class UserDataStreaming(Database, BinanceApi):
    def __init__(self) -> None:
        self.streaming_db = self._db
        self.session = independent_session()
        self.bot_controller = BotTableCrud(session=self.session)
        self.user_data_client: AsyncSpotWebsocketStreamClient | None = None

    def on_error(self, socket, error):
        logging.error(f"User data streaming error: {error}")

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

    async def start(self):
        listen_key = self.get_listen_key()
        self.user_data_client = AsyncSpotWebsocketStreamClient(
            on_message=self.on_user_data_message,
            on_error=self.on_error,
        )
        await self.user_data_client.connect()
        await self.user_data_client.user_data(listen_key)
        logging.info("User data WebSocket connected")

    async def run_forever(self):
        if not self.user_data_client:
            await self.start()
        while True:
            await asyncio.sleep(60)

    def on_user_data_message(self, socket, raw):
        try:
            res = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        except Exception:
            logging.error(f"Invalid user data payload: {raw}")
            return
        event = res.get("e")
        if not event:
            return
        if event == "executionReport":
            try:
                self.update_order_data(res)
            except Exception as e:
                logging.error(f"Failed updating order: {e}")
        elif event == "outboundAccountPosition":
            logging.debug("Outbound account position update")
        elif event == "balanceUpdate":
            logging.debug("Balance update event")
