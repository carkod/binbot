import json
import threading
import requests
from account.account import Account
from apis import BinanceApi
from deals.controllers import CreateDealController
from threads import market_update_thread
from tools.handle_error import handle_error
from websocket import WebSocketApp


class OrderUpdates(BinanceApi):
    def __init__(self, app):
        self.active_ws = None
        self.listenkey = None

        # Websockets do not get responses and requests
        # Therefore there is no context
        self.app = app

    def get_listenkey(self):
        # Get data for a single crypto e.g. BTT in BNB market
        headers = {"X-MBX-APIKEY": self.key}

        # Response after request
        res = requests.post(url=self.user_data_stream, headers=headers)
        handle_error(res)
        data = res.json()
        return data

    def restart_market_updates(self):
        """
        Restart market_updates threads after list of active bots altered
        """
        print("Restarting market_updates")
        # Notify market updates websockets to update
        for thread in threading.enumerate():
            if thread.name == "market_updates_thread":
                thread._target.__self__.markets_streams.close()
                market_update_thread()
        print("Finished restarting market_updates")
        return

    async def run_stream(self):
        if not self.active_ws or not self.listen_key:
            self.listen_key = self.get_listenkey()["listenKey"]

        ws = WebSocketApp(
            f"{self.streams_url}{self.listen_key}",
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )
        await ws.run_forever(ping_interval=70)

    def close_stream(self, ws, close_status_code, close_msg):
        print("Active socket closed", close_status_code, close_msg)

    def on_open(self, *args, **kwargs):
        print("Orders websockets opened")

    def on_error(self, ws, error):
        print(f"Order Websocket error: {error}")
        self.run_stream()

    def on_message(self, wsapp, message):
        response = json.loads(message)
        try:
            result = response["data"]
        except KeyError as error:
            print(f"Error: {error}")

        if "e" in result and result["e"] == "executionReport":
            self.process_report_execution(result)

    def process_report_execution(self, result):
        # Parse result. Print result for raw result from Binance
        order_id = result["i"]

        if result["X"] == "FILLED":
            # Close successful take_profit
            self.app.db.bots.update_one(
                {
                    "orders": {
                        "$elemMatch": {"deal_type": "take_profit", "order_id": order_id}
                    }
                },
                {
                    "$set": {"status": "completed", "deal.current_price": result["p"], "deal.sell_price": result["p"]},
                    "$inc": {"deal.commission": float(result["n"])},
                    "$push": {"errors": "Bot take_profit completed!"},
                },
            )
            # Close successful orders
            self.app.db.bots.update_one(
                {
                    "orders": {
                        "$elemMatch": {
                            "deal_type": "trailling_stop_loss",
                            "order_id": order_id,
                        }
                    }
                },
                {
                    "$set": {"status": "completed", "deal.current_price": result["p"], "deal.sell_price": result["p"]},
                    "$inc": {"deal.commission": float(result["n"])},
                    "$push": {"errors": "Bot trailling_stop_loss completed!"},
                },
            )

        else:
            print(
                f"No bot found with order client order id: {order_id}. Order status: {result['X']}"
            )