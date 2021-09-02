import json
import os
import time
import threading
import pandas
import requests
from api.app import create_app
from api.deals.deal_updates import DealUpdates
from api.telegram_bot import TelegramBot
from api.tools.handle_error import handle_error
from api.account.account import Account
from websocket import WebSocketApp
from time import sleep
from datetime import datetime, timedelta
from api.tools.round_numbers import supress_notation

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
        self.telegram_bot = TelegramBot()
        self.time_to_death = datetime.now() + timedelta(hours=24)

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

    def _send_msg(self, msg):
        """
        Send message with telegram bot
        To avoid Conflict - duplicate Bot error
        /t command will still be available in telegram bot
        """
        if not hasattr(self.telegram_bot, "updater"):
            self.telegram_bot.run_bot()

        self.telegram_bot.send_msg(msg)
        return

    def _run_streams(self, stream, index):
        string_params = "/".join(stream)
        url = f"{self.base}/stream?streams={string_params}"
        ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )
        worker_thread = threading.Thread(name=f"market_updates_{index}", target=ws.run_forever)
        worker_thread.start()

    def start_stream(self):
        raw_symbols = self.get_symbols_raw().json
        markets = set(raw_symbols["data"])
        black_list = set(self.black_list)
        self.list_markets = markets - black_list
        params = []
        for market in list(self.list_markets):
            params.append(f"{market.lower()}@kline_{self.interval}")

        stream_1 = params[:self.max_request]
        stream_2 = params[(self.max_request + 1):]

        self._run_streams(stream_1, 1)
        self._run_streams(stream_2, 2)

    def close_stream(self, ws):
        ws.close()
        print("Active socket closed")
        sleep(10)
        self.start_stream()

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

        delta = self.time_to_death - datetime.now()
        print(delta)

        if "result" in json_response and json_response["result"]:
            print(f'Subscriptions: {json_response["result"]}')

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

            # Stop loss
            if bot["deal"]["stop_loss"]:
                deal = DealUpdates(bot)
                deal.update_stop_limit(close_price)

            if bot["trailling"] == "true" and "trailling_profit" in bot["deal"] and float(close_price) > float(bot["deal"]["trailling_profit"]):
                price = float(bot["deal"]["current_price"]) - (float(bot["trailling_deviation"]) * float(bot["deal"]["current_price"]))
                if float(close_price) < float(price):
                    deal = DealUpdates(bot)
                    print("Trailling take profit executed!")
                    # No need to pass price to update deal
                    # The price already matched market price
                    deal.trailling_take_profit(price)

            # Open safety orders
            # When bot = None, when bot doesn't exist (unclosed websocket)
            if (
                bot
                and "safety_order_prices" in bot["deal"]
                and len(bot["deal"]["safety_order_prices"]) > 0
            ):
                for key, value in bot["deal"]["safety_order_prices"]:
                    # Index is the ID of the safety order price that matches safety_orders list
                    if float(value) >= float(close_price):
                        deal = DealUpdates(bot)
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
            data = self._get_candlestick(symbol, self.interval)
            volatility = pandas.Series(data[0]["close"]).astype(float).std(0)

            ma_100 = data[1]["y"]

            # raw df
            df = pandas.DataFrame(self._get_raw_klines(symbol, 1000))
            df["candle_spread"] = abs(
                pandas.to_numeric(df[1]) - pandas.to_numeric(df[4])
            )
            curr_candle_spread = df["candle_spread"][df.shape[0] - 1]
            avg_candle_spread = df["candle_spread"].median()
            candlestick_signal = (
                "positive"
                if float(curr_candle_spread) > float(avg_candle_spread)
                else "negative"
            )

            df["volume_spread"] = abs(
                pandas.to_numeric(df[1]) - pandas.to_numeric(df[4])
            )
            curr_volume_spread = df["volume_spread"][df.shape[0] - 1]
            avg_volume_spread = df["volume_spread"].median()
            # volume_signal = "positive" if float(curr_candle_spread) > float(avg_candle_spread) else "negative"

            high_price = max(data[0]["high"])
            low_price = max(data[0]["low"])
            spread = (float(high_price) / float(low_price)) - 1

            price_change_24 = self._get_24_ticker(symbol)["priceChangePercent"]

            all_time_low = pandas.to_numeric(df[3]).min()

            setObject = {
                "current_price": result["k"]["c"],
                "volatility": volatility,
                "last_volume": float(result["k"]["v"]) + float(result["k"]["q"]),
                "spread": spread,
                "price_change_24": float(
                    price_change_24
                ),  # MongoDB can't sort string decimals
                "candlestick_signal": candlestick_signal,
                "blacklisted": False,
                "blacklisted_reason": None
            }

            if symbol in self.black_list:
                setObject["blacklisted"] = True

            if symbol not in self.last_processed_kline:
                if float(close_price) > float(open_price) and (curr_candle_spread > (avg_candle_spread * 2) and curr_volume_spread > avg_volume_spread) and (close_price > ma_100[len(ma_100)-1]):
                    # Send Telegram
                    msg = f"- Candlesick jump <strong>{symbol}</strong> \n- Spread {supress_notation(spread, 2)} \n- Upward trend - https://www.binance.com/en/trade/{symbol}"

                    if close_price < float(all_time_low):
                        msg = f"- Candlesick jump and all time high <strong>{symbol}</strong> \n- Spread {supress_notation(spread, 2)} \n- Upward trend - https://www.binance.com/en/trade/{symbol}"

                    if msg:
                        self._send_msg(msg)

                # Update Current price
                self.app.db.correlations.find_one_and_update(
                    {"market": symbol},
                    {
                        "$currentDate": {"lastModified": True},
                        "$set": setObject,
                    },
                )

                print(f"{symbol} Updated, interval: {self.interval}")

                self.last_processed_kline[symbol] = time.time()
                # If more than half an hour (interval = 30m) has passed
                # Then we should resume sending signals for given symbol
                if (
                    float(time.time()) - float(self.last_processed_kline[symbol])
                ) > 400:
                    del self.last_processed_kline[symbol]
