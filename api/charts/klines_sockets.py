import json
import os

from api.deals.deal_updates import DealUpdates
from websocket import WebSocketApp
import threading
from api.app import create_app
class KlineSockets:
    def __init__(self, subs=True):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.user_datastream_listenkey = os.getenv("USER_DATA_STREAM")
        self.all_orders_url = os.getenv("ALL_ORDERS")
        self.order_url = os.getenv("ORDER")

        # streams
        self.base = os.getenv("WS_BASE")
        self.path = "/ws"
        self.subs = subs
        self.interval = "1m"

    def start_stream(self):
        app = create_app()
        params = []
        bots = app.db.bots.find({"active": "true"})
        for bot in list(bots):
            params.append(f'{bot["pair"].lower()}@kline_{self.interval}')

        string_params = "/".join(params)
        url = f"{self.base}{self.path}/{string_params}"
        ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )
        wst = threading.Thread(target=ws.run_forever)
        wst.start()

    def close_stream(self, ws):
        ws.close()
        print("Kline stream closed")

    def on_open(self, ws):
        print("Klines stream opened")
        # app = create_app()
        # params = []
        # bots = app.db.bots.find({"active": "true"})
        # for bot in list(bots):
        #     params.append(f'{bot["pair"].lower()}@kline_{self.interval}')

        # request = {
        #     "method": "SUBSCRIBE" if self.subs else "UNSUBSCRIBE",
        #     "params": params,
        #     "id": 2,
        # }
        # ws.send(json.dumps(request))

    def on_error(self, ws, error):
        print(f"Websocket error: {error}")

    def on_message(self, wsapp, message):
        response = json.loads(message)

        if "result" in response and response["result"]:
            print(f'Subscriptions: {response["result"]}')

        elif "e" in response and response["e"] == "kline":
            self.process_kline_stream(response)

        else:
            print(f"Error: {response}")

    def process_kline_stream(self, result):
        if result["k"]["x"]:
            close_price = result["k"]["c"]
            symbol = result["k"]["s"]
            app = create_app()

            # Update Current price
            bot = app.db.bots.find_one_and_update(
                {"pair": symbol}, {"$set": {"deal.current_price": close_price}}
            )

            # Open safety orders
            if "safety_order_prices" in bot["deal"]:
                for index, price in enumerate(bot["deal"]["safety_order_prices"]):
                    # Index is the ID of the safety order price that matches safety_orders list
                    if float(price) == float(close_price):
                        deal = DealUpdates(bot, app)
                        # No need to pass price to update deal
                        # The price already matched market price
                        deal.so_update_deal(index)
