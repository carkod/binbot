import json
import os

import requests
from api.tools.handle_error import handle_error
from websocket import WebSocketApp
from api.app import create_app
import pandas
import math
class MarketUpdates:

    key = os.getenv("BINANCE_KEY")
    secret = os.getenv("BINANCE_SECRET")
    user_datastream_listenkey = os.getenv("USER_DATA_STREAM")
    all_orders_url = os.getenv("ALL_ORDERS")
    order_url = os.getenv("ORDER")
    candlestick_url = os.getenv("CANDLESTICK")

    bb_base_url = f'{os.getenv("FLASK_DOMAIN")}'
    bb_candlestick_url = f"{bb_base_url}/charts/candlestick"

    # streams
    base = os.getenv("WS_BASE")

    def __init__(self, interval="1m"):
        self.list_markets = []
        self.markets_streams = None
        self.app = create_app()
        self.interval = interval

    def _get_candlestick(self, market):
        url = f"{self.bb_candlestick_url}/{market}/{self.interval}"
        res = requests.get(url=url)
        handle_error(res)
        return res.json()

    def start_stream(self):
        self.list_markets = self.app.db.correlations.distinct("market_a")
        params = []
        for market in self.list_markets:
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

        else:
            print(f"Error: {response}")

    def _weak_signals(self, close_price, open_price, ma_7, ma_25, ma_100):
        """
        Weak bullying
        - This detects prices that go up and go down (both bullying and bearing)
        - Weak signals, as they happen more frequently and do not entail a lot of profit
        """
        bollinguer_bands_signal = None

        # MA-25 line crossed MA-7
        # Using isclose relative tolerance, as values don't usually match
        ma_25_crossed_7 = (
            True
            if math.isclose(ma_25[len(ma_25) - 1], ma_7[len(ma_7) - 1], rel_tol=1e-3)
            else False
        )
        # Bottom of candlestick crossed MA-100
        top_green_candle = True if close_price > ma_25[len(ma_25) - 1] else False
        # Tip of candlestick crossed MA-100
        bottom_green_candle = True if open_price < ma_25[len(ma_25) - 1] else False

        # Downward/Bearing conditions
        top_red_candle = True if open_price > ma_25[len(ma_25) - 1] else False
        bottom_red_candle = True if close_price < ma_25[len(ma_25) - 1] else False

        if ma_25_crossed_7:
            if top_green_candle and bottom_green_candle:
                bollinguer_bands_signal = "WEAK BUY"

            if top_red_candle and bottom_red_candle:
                bollinguer_bands_signal = "WEAK SELL"

        return bollinguer_bands_signal

    def _strong_signals(self, close_price, open_price, ma_7, ma_25, ma_100):
        """
        Strong signals use the MA_100
        Happen less frequently, but there is a higher profit margin
        Higher volatility
        """

        bollinguer_bands_signal = None

        # MA-25 line crossed MA-100
        ma_25_crossed = (
            True
            if math.isclose(
                ma_25[len(ma_25) - 1], ma_100[len(ma_100) - 1], rel_tol=1e-3
            )
            else False
        )
        # MA-7 line crossed MA-100
        ma_7_crossed = (
            True
            if math.isclose(ma_7[len(ma_7) - 1], ma_100[len(ma_100) - 1], rel_tol=1e-3)
            else False
        )

        # Upward/Bullying conditions
        # Bottom of candlestick crossed MA-100
        top_green_candle = True if close_price > ma_100[len(ma_100) - 1] else False
        # Tip of candlestick crossed MA-100
        bottom_green_candle = True if open_price > ma_100[len(ma_100) - 1] else False
        # Second to last Tip of candlestick crossed MA-100
        previous_top_green_candle = (
            True if open_price > ma_100[len(ma_100) - 2] else False
        )

        # Downward/Bearing conditions
        # Bottom of red candlestick crossed MA-100
        top_red_candle = True if open_price < ma_100[len(ma_100) - 1] else False
        # Tip of red candlestick crossed MA-100
        bottom_red_candle = True if close_price < ma_100[len(ma_100) - 1] else False
        # Second to last Tip of candlestick crossed MA-100
        previous_bottom_red_candle = (
            True if close_price < ma_100[len(ma_100) - 2] else False
        )

        # Strong signals
        if ma_25_crossed and ma_7_crossed:
            if top_green_candle and bottom_green_candle and previous_top_green_candle:
                bollinguer_bands_signal = "STRONG BUY"

            if top_red_candle and bottom_red_candle and previous_bottom_red_candle:
                bollinguer_bands_signal = "STRONG SELL"

        return bollinguer_bands_signal

    def process_kline_stream(self, result):
        if result["k"]["x"]:
            close_price = float(result["k"]["c"])
            open_price = float(result["k"]["o"])
            symbol = result["k"]["s"]
            print(f"market_update kline {symbol}")
            data = self._get_candlestick(symbol)["trace"]
            print("market_update kline after data")
            ma_100 = data[1]["y"]
            ma_25 = data[2]["y"]
            ma_7 = data[3]["y"]
            volatility = pandas.Series(data[0]["close"]).astype(float).std(0)

            highest_price = max(data[0]["high"])
            lowest_price = max(data[0]["low"])
            spread = ((float(highest_price) / float(lowest_price)) - 1)

            bollinguer_bands_signal = None

            bollinguer_bands_signal = self._strong_signals(
                close_price, open_price, ma_7, ma_25, ma_100
            )

            if not bollinguer_bands_signal:
                bollinguer_bands_signal = self._weak_signals(
                    close_price, open_price, ma_7, ma_25, ma_100
                )
            # Update Current price
            if bollinguer_bands_signal:
                self.app.db.correlations.find_one_and_update(
                    {"market_a": symbol},
                    {
                        "$currentDate": {"lastModified": True},
                        "$set": {
                            "current_price": result["k"]["c"],
                            "bollinguer_bands_signal": bollinguer_bands_signal,
                            "volatility": volatility,
                            "last_volume": float(result["k"]["v"]) + float(result["k"]["q"]),
                            "spread": spread
                        },
                    },
                )
            print(f"{symbol} Bollinguer signal: {bollinguer_bands_signal}, interval: {self.interval}")
