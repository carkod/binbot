import json

import requests
from api.account.assets import Assets
from api.app import create_app
from api.deals.deal_updates import DealUpdates
from api.deals.models import Deal
from api.tools.handle_error import handle_error
from websocket import WebSocketApp
from api.apis import BinanceApi

class OrderUpdates(BinanceApi):
    def __init__(self):
        self.active_ws = None
        self.listenkey = None

        # Websockets do not get responses and requests
        # Therefore there is no context
        self.app = create_app()

    def get_listenkey(self):
        # Get data for a single crypto e.g. BTT in BNB market
        params = []
        headers = {"X-MBX-APIKEY": self.key}

        # Response after request
        res = requests.post(url=self.user_data_stream, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data

    def run_stream(self):
        if not self.active_ws or not self.listen_key:
            self.listen_key = self.get_listenkey()["listenKey"]

        ws = WebSocketApp(
            f'{self.streams_url}{self.listen_key}',
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )
        ws.run_forever(ping_interval=70)

    def close_stream(self, ws, close_status_code, close_msg):
        print("Active socket closed", close_status_code, close_msg)

    def on_open(self, ws):
        print("Orders websockets opened")

    def on_error(self, ws, error):
        print(f"Order Websocket error: {error}")
        if error.args[0] == "Connection to remote host was lost.":
            self.run_stream()

    def on_message(self, wsapp, message):
        response = json.loads(message)
        try:
            result = response["data"]
        except KeyError:
            print(f"Error: {result}")

        if "e" in result and result["e"] == "executionReport":
            self.process_report_execution(result)

        # account balance has changed and contains the assets that were possibly changed by the event that generated the balance change
        # https://binance-docs.github.io/apidocs/spot/en/#payload-account-update
        if "e" in result and result["e"] == "outboundAccountPosition":
            self.process_account_update(result)

    def process_report_execution(self, result):
        # Parse result. Print result for raw result from Binance
        order_id = result["i"]

        if result["X"] == "FILLED":
            # Close successful orders
            bot = self.app.db.bots.find_one_and_update(
                {
                    "orders": {
                        "$elemMatch": {"deal_type": "take_profit", "order_id": order_id}
                    }
                },
                {
                    "$set": {"status": "inactive", "deal.current_price": result["p"]},
                    "$inc": {"deal.commission": float(result["n"])},
                },
            )
            if bot:
                print(f"Bot take_profit completed! Bot {bot['_id']} deactivated")
                # Logic to convert market coin into GBP here
                Deal(bot).buy_gbp_balance()

            # Update Safety orders
            bot = self.app.db.bots.find_one(
                {
                    "orders": {
                        "$elemMatch": {
                            "deal_type": "safety_order",
                            "order_id": order_id,
                        }
                    }
                }
            )

            if bot:
                # It is a safety order, now find safety order deal price
                deal = DealUpdates(bot)
                deal.default_deal.update(bot)
                deal.update_take_profit(order_id)

        else:
            print(f"No bot found with order client order id: {order_id}")

    def process_account_update(self, result):
        balance = result["B"]
        if len(balance) > 0:
            assets = Assets()
            assets.store_balance()
