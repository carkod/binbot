import json
import os
import requests
import time
from api.tools.handle_error import handle_error
from websocket import WebSocketApp
from api.app import create_app
import pandas
from api.research.signals import MASignals
from api.deals.deal_updates import DealUpdates
from api.telegram_bot import TelegramBot
class MarketUpdates:

    key = os.getenv("BINANCE_KEY")
    secret = os.getenv("BINANCE_SECRET")
    user_datastream_listenkey = os.getenv("USER_DATA_STREAM")
    all_orders_url = os.getenv("ALL_ORDERS")
    order_url = os.getenv("ORDER")
    candlestick_url = os.getenv("CANDLESTICK")

    bb_base_url = f'{os.getenv("FLASK_DOMAIN")}'
    bb_candlestick_url = f"{bb_base_url}/charts/candlestick"
    bb_24_ticker_url = f"{bb_base_url}/account/ticker24"

    # streams
    base = os.getenv("WS_BASE")

    def __init__(self, interval="30m"):
        self.list_markets = []
        self.markets_streams = None
        self.app = create_app()
        self.interval = interval
        self.last_processed_kline = {}
        self.black_list = ["TRXBTC", "WPRBTC", "NEOBTC", "BTCUSDT", "ETHBTC", "BNBBTC", "ETHBTC", "LTCBTC", "ETHUSDT", "ETCBTC", "BNBETH", "EOSBTC", "DASHETH", "FUNBTC", "EOSBTC", "SNGLSBTC", "YOYOBTC", "LINKETH", "XVGBTC", "SNTBTC", "DASHBTC", "VIBBTC"]

    def _get_raw_klines(self, pair):
        params = {"symbol": pair, "interval": self.interval, "limit": "200"}
        res = requests.get(url=self.candlestick_url, params=params)
        handle_error(res)
        return res.json()

    def _get_candlestick(self, market):
        url = f"{self.bb_candlestick_url}/{market}/{self.interval}"
        res = requests.get(url=url)
        handle_error(res)
        return res.json()

    def _get_24_ticker(self, market):
        url = f"{self.bb_24_ticker_url}/{market}"
        res = requests.get(url=url)
        handle_error(res)
        data = res.json()["data"]
        return data

    def start_stream(self):
        markets = set(self.app.db.correlations.distinct("market_a"))
        black_list = set(self.black_list)
        self.list_markets = markets - black_list
        params = []
        for market in list(self.list_markets):
            params.append(f"{market.lower()}@kline_{self.interval}")

        string_params = "/".join(params)
        url = f"{self.base}/ws/{string_params}"
        ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )
        # For thread management
        self.markets_streams = ws
        ws.run_forever()

    def close_stream(self, ws):
        ws.close()
        print("Active socket closed")
        self.start_stream()

    def on_open(self, ws):
        print("Market data updates socket opened")

    def on_error(self, ws, error):
        print(f"Websocket error: {error}")
        ws.close()
        if error == "[Errno 104] Connection reset by peer":
            self.start_stream()

    def on_message(self, wsapp, message):
        response = json.loads(message)
        if "result" in response and response["result"]:
            print(f'Subscriptions: {response["result"]}')

        elif "e" in response and response["e"] == "kline":
            self.process_kline_stream(response)
            self.process_deals(response)

        else:
            print(f"Error: {response}")

    def process_deals(self, result):
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        if result["k"]["x"]:
            close_price = result["k"]["c"]
            symbol = result["k"]["s"]
            app = create_app()

            # Update Current price
            bot = app.db.bots.find_one_and_update(
                {"pair": symbol}, {"$set": {"deal.current_price": close_price}}
            )

            # Open safety orders
            # When bot = None, when bot doesn't exist (unclosed websocket)
            if bot and "safety_order_prices" in bot["deal"] and len(bot["deal"]["safety_order_prices"]) > 0:
                for key, value in bot["deal"]["safety_order_prices"]:
                    # Index is the ID of the safety order price that matches safety_orders list
                    if float(value) >= float(close_price):
                        deal = DealUpdates(bot, app)
                        print("Update deal executed")
                        # No need to pass price to update deal
                        # The price already matched market price
                        deal.so_update_deal(key)

    def process_kline_stream(self, result):
        """
        Updates market data in DB for research
        """
        # Check if closed result["k"]["x"]
        if result["k"] and result["k"]["s"]:
            close_price = float(result["k"]["c"])
            open_price = float(result["k"]["o"])
            symbol = result["k"]["s"]
            data = self._get_candlestick(symbol)["trace"]
            ma_100 = data[1]["y"]
            ma_25 = data[2]["y"]
            ma_7 = data[3]["y"]
            volatility = pandas.Series(data[0]["close"]).astype(float).std(0) 

            # raw df
            df = pandas.DataFrame(self._get_raw_klines(symbol))
            df["candle_spread"] = abs(pandas.to_numeric(df[1]) - pandas.to_numeric(df[4]))
            curr_candle_spread = df["candle_spread"][df.shape[0] - 1]
            avg_candle_spread = df["candle_spread"].median()
            candlestick_signal = "positive" if float(curr_candle_spread) > float(avg_candle_spread) else "negative"

            df["volume_spread"] = abs(pandas.to_numeric(df[1]) - pandas.to_numeric(df[4]))
            curr_volume_spread = df["volume_spread"][df.shape[0] - 1]
            avg_volume_spread = df["volume_spread"].median()
            volume_signal = "positive" if float(curr_candle_spread) > float(avg_candle_spread) else "negative"

            highest_price = max(data[0]["high"])
            lowest_price = max(data[0]["low"])
            spread = (float(highest_price) / float(lowest_price)) - 1

            price_change_24 = self._get_24_ticker(symbol)["priceChangePercent"]

            setObject = {
                "current_price": result["k"]["c"],
                "volatility": volatility,
                "last_volume": float(result["k"]["v"]) + float(result["k"]["q"]),
                "spread": spread,
                "price_change_24": float(price_change_24),  # MongoDB can't sort string decimals
                "candlestick_signal": candlestick_signal,
            }

            setObject = MASignals().get_signals(close_price, open_price, ma_7, ma_25, ma_100, setObject)

            if symbol not in self.last_processed_kline:
                if (
                    float(close_price) > float(open_price) and (curr_candle_spread > avg_candle_spread and curr_volume_spread > avg_volume_spread)
                ):
                    # Send Telegram
                    msg = f"Open signal {symbol} - Candlestick jump http://binbot.in/admin/research"
                    TelegramBot().send_msg(msg)
                    self.last_processed_kline[symbol] = time.time()
                    # If more than half an hour (interval = 30m) has passed
                    # Then we should resume sending signals for given symbol
                    if (float(time.time()) - float(self.last_processed_kline[symbol])) > 1800:
                        del self.last_processed_kline[symbol]

                # Update Current price
                self.app.db.correlations.find_one_and_update(
                    {"market_a": symbol},
                    {
                        "$currentDate": {"lastModified": True},
                        "$set": setObject,
                    },
                )

                print(f"{symbol} Updated, interval: {self.interval}")
