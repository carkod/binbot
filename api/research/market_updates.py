import json
import os
import threading
import requests
from api.app import create_app
from api.deals.deal_updates import DealUpdates
from api.tools.handle_error import handle_error
from api.account.account import Account
from websocket import WebSocketApp

class MarketUpdates(Account):
    """
    Further explanation in docs/market_updates.md
    """

    key = os.getenv("BINANCE_KEY")
    secret = os.getenv("BINANCE_SECRET")
    user_datastream_listenkey = os.getenv("USER_DATA_STREAM")
    all_orders_url = os.getenv("ALL_ORDERS")
    order_url = os.getenv("ORDER")
    candlestick_url = os.getenv("CANDLESTICK")

    bb_base_url = f'{os.getenv("FLASK_DOMAIN")}'
    bb_candlestick_url = f"{bb_base_url}/charts/candlestick"
    bb_24_ticker_url = f"{bb_base_url}/account/ticker24"
    bb_symbols_raw = f"{bb_base_url}/account/symbols/raw"

    # streams
    base = os.getenv("WS_BASE")

    def __init__(self, interval="1h"):
        self.list_markets = []
        self.markets_streams = None
        self.app = create_app()
        self.interval = interval
        self.last_processed_kline = {}
        # This blacklist is necessary to keep prod and local DB synched
        self.black_list = [
            "TRXBTC",
            "WPRBTC",
            "NEOBTC",
            "BTCUSDT",
            "ETHBTC",
            "BNBBTC",
            "ETHBTC",
            "LTCBTC",
            "ETHUSDT",
            "ETCBTC",
            "BNBETH",
            "EOSBTC",
            "DASHETH",
            "FUNBTC",
            "EOSBTC",
            "SNGLSBTC",
            "YOYOBTC",
            "LINKETH",
            "XVGBTC",
            "SNTBTC",
            "DASHBTC",
            "VIBBTC",
            "XMRBTC",
            "WAVESBNB",
            "QSPBTC",
            "WPRBTC",
            "MKRBTC",
            "MKRUSDT",
            "MKRBUSD",
            "MKRBNB",
            "MTHBTC",
            "GASBTC",  # test
            "OMGBTC",
            "LINKBTC",
            "QTUMBTC",
            "BCHBTC",
            "BCHUSDT",
            "BCHBUSD",
            "BCHBNB",
            "BCHTUSD",
            "BCHUSDC"
        ]
        self.max_request = 960  # Avoid HTTP 411 error by splitting into multiple websockets

    def _get_raw_klines(self, pair, limit="200"):
        params = {"symbol": pair, "interval": self.interval, "limit": limit}
        res = requests.get(url=self.candlestick_url, params=params)
        handle_error(res)
        return res.json()

    def _get_candlestick(self, market, interval):
        url = f"{self.bb_candlestick_url}/{market}/{interval}"
        res = requests.get(url=url)
        handle_error(res)
        data = res.json()
        return data["trace"]

    def _get_24_ticker(self, market):
        url = f"{self.bb_24_ticker_url}/{market}"
        res = requests.get(url=url)
        handle_error(res)
        data = res.json()["data"]
        return data

    def start_stream(self):
        """
        Get list of cryptos currently trading bots

        """
        markets = list(self.app.db.bots.distinct("pair", {"status": "active"}))
        self.list_markets = set(markets) - set(self.black_list)
        params = []
        for market in list(self.list_markets):
            params.append(f"{market.lower()}@kline_{self.interval}")

        string_params = "/".join(params)
        url = f"{self.base}/stream?streams={string_params}"
        ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )
        worker_thread = threading.Thread(name="market_updates", target=ws.run_forever)
        worker_thread.start()

    def close_stream(self, ws, close_status_code, close_msg):
        ws.close()
        print("Active socket closed", close_status_code, close_msg)

    def on_open(self, ws):
        print("Market data updates socket opened")

    def on_error(self, ws, error):
        print(f"Websocket error: {error}")
        if error.args[0] == "Connection to remote host was lost.":
            self.start_stream()
        ws.close()

    def on_message(self, ws, message):
        json_response = json.loads(message)
        response = json_response["data"]

        if "result" in json_response and json_response["result"]:
            print(f'Subscriptions: {json_response["result"]}')

        elif "e" in response and response["e"] == "kline":
            self.process_deals(response)

        else:
            print(f"Error: {response}")

    def process_deals(self, result):
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        # result["k"]["x"]
        if "k" in result:
            close_price = result["k"]["c"]
            symbol = result["k"]["s"]

            # Update Current price
            bot = self.app.db.bots.find_one_and_update(
                {"pair": symbol}, {"$set": {"deal.current_price": close_price}}
            )
            if bot and "deal" in bot:
                # Stop loss
                if "stop_loss" in bot["deal"]:
                    deal = DealUpdates(bot)
                    deal.update_stop_limit(close_price)

                if bot["trailling"] == "true":
                    # Check if trailling profit reached the first time
                    current_take_profit_price = float(bot["deal"]["buy_price"]) * (1 + (float(bot["take_profit"]) / 100))
                    if float(close_price) >= current_take_profit_price:
                        # Update deal take_profit
                        bot["deal"]["take_profit_price"] = bot["deal"]["trailling_profit"]
                        # Update trailling_stop_loss
                        bot["deal"]["trailling_stop_loss_price"] = float(current_take_profit_price) - (float(current_take_profit_price) * (float(bot["trailling_deviation"]) / 100))

                        updated_bot = self.app.db.bots.find_one_and_update(
                            {"pair": symbol}, {"$set": {"deal": bot["deal"]}}
                        )
                        if not updated_bot:
                            print(f"Error updating trailling order {updated_bot}")

                    if "trailling_stop_loss_price" in bot["deal"]:
                        price = bot["deal"]["trailling_stop_loss_price"]
                        if float(close_price) <= float(price):
                            deal = DealUpdates(bot)
                            deal.trailling_take_profit(price)

                # Open safety orders
                # When bot = None, when bot doesn't exist (unclosed websocket)
                if "safety_order_prices" in bot["deal"] and len(bot["deal"]["safety_order_prices"]) > 0:
                    for key, value in bot["deal"]["safety_order_prices"]:
                        # Index is the ID of the safety order price that matches safety_orders list
                        if float(value) >= float(close_price):
                            deal = DealUpdates(bot)
                            print("Update deal executed")
                            # No need to pass price to update deal
                            # The price already matched market price
                            deal.so_update_deal(key)
            return
