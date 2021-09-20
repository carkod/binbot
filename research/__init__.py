import json
import os
import time
import threading
import pandas
import requests
from telegram_bot import TelegramBot
from utils import handle_error
from websocket import WebSocketApp
from utils import supress_notation
from pymongo import MongoClient
from apis import BinanceApi
from dotenv import load_dotenv
from time import sleep

load_dotenv()

mongo = MongoClient(
    os.environ["MONGO_HOSTNAME"],
    int(os.environ["MONGO_PORT"]),
    username=os.environ["MONGO_AUTH_USERNAME"],
    password=os.environ["MONGO_AUTH_PASSWORD"],
    authSource=os.environ["MONGO_AUTH_DATABASE"],
)

bb_base_url = f'{os.getenv("RESEARCH_FLASK_DOMAIN")}'
bb_candlestick_url = f"{bb_base_url}/charts/candlestick"
bb_24_ticker_url = f"{bb_base_url}/account/ticker24"
bb_symbols_raw = f"{bb_base_url}/account/symbols/raw"

# streams
base = os.getenv("WS_BASE")

list_markets = []
markets_streams = None
interval = "1h"
last_processed_kline = {}
# This blacklist is necessary to keep prod and local DB synched
black_list = [
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
    "BCHUSDC",
]
telegram_bot = TelegramBot()
max_request = 950  # Avoid HTTP 411 error by separating streams


def _get_candlestick(market, interval):
    url = f"{bb_candlestick_url}/{market}/{interval}"
    res = requests.get(url=url)
    res.raise_for_status()
    data = res.json()
    return data["trace"]


def _get_24_ticker(market):
    url = f"{bb_24_ticker_url}/{market}"
    res = requests.get(url=url)
    handle_error(res)
    data = res.json()["data"]
    return data


def _send_msg(msg):
    """
    Send message with telegram bot
    To avoid Conflict - duplicate Bot error
    /t command will still be available in telegram bot
    """
    if not hasattr(telegram_bot, "updater"):
        telegram_bot.run_bot()

    telegram_bot.send_msg(msg)
    return


def close_stream(ws, close_status_code, close_msg):
    print("Active socket closed", close_status_code, close_msg)


def _run_streams(stream, index):
    string_params = "/".join(stream)
    url = f"{base}/stream?streams={string_params}"
    ws = WebSocketApp(
        url,
        on_open=on_open,
        on_error=on_error,
        on_close=close_stream,
        on_message=on_message,
    )
    worker_thread = threading.Thread(
        name=f"market_updates_{index}", target=ws.run_forever
    )
    worker_thread.start()


def start_stream():
    raw_symbols = BinanceApi()._ticker_price()
    markets = set([item["symbol"] for item in raw_symbols])
    subtract_list = set(black_list)
    list_markets = markets - subtract_list
    params = []
    for market in list(list_markets):
        params.append(f"{market.lower()}@kline_{interval}")

    stream_1 = params[:max_request]
    stream_2 = params[(max_request + 1) :]

    _run_streams(stream_1, 1)
    _run_streams(stream_2, 2)


def on_open(ws):
    print("Market data updates socket opened")


def on_error(ws, error):
    print(f"Websocket error: {error}")
    if error.args[0] == "Connection to remote host was lost.":
        print("Restarting in 30 seconds...")
        sleep(30)
        start_stream()


def on_message(ws, message):
    json_response = json.loads(message)
    response = json_response["data"]

    if "result" in json_response and json_response["result"]:
        print(f'Subscriptions: {json_response["result"]}')

    elif "e" in response and response["e"] == "kline":
        process_kline_stream(response)

    else:
        print(f"Error: {response}")


def process_kline_stream(result):
    """
    Updates market data in DB for research
    """
    # Check if closed result["k"]["x"]
    if "k" in result and "s" in result["k"]:
        close_price = float(result["k"]["c"])
        open_price = float(result["k"]["o"])
        symbol = result["k"]["s"]
        data = _get_candlestick(symbol, interval)
        ma_100 = data[1]["y"]

        # raw df
        klines = BinanceApi()._get_raw_klines(symbol, 1000)
        df = pandas.DataFrame(klines)
        df["candle_spread"] = abs(pandas.to_numeric(df[1]) - pandas.to_numeric(df[4]))
        curr_candle_spread = df["candle_spread"][df.shape[0] - 1]
        avg_candle_spread = df["candle_spread"].median()

        df["volume_spread"] = abs(pandas.to_numeric(df[1]) - pandas.to_numeric(df[4]))
        curr_volume_spread = df["volume_spread"][df.shape[0] - 1]
        avg_volume_spread = df["volume_spread"].median()

        high_price = max(data[0]["high"])
        low_price = max(data[0]["low"])
        spread = (float(high_price) / float(low_price)) - 1

        all_time_low = pandas.to_numeric(df[3]).min()

        if symbol not in last_processed_kline:
            if (
                float(close_price) > float(open_price)
                and (
                    curr_candle_spread > (avg_candle_spread * 2)
                    and curr_volume_spread > avg_volume_spread
                )
                and (close_price > ma_100[len(ma_100) - 1])
            ):
                # Send Telegram
                msg = f"- Candlesick jump <strong>{symbol}</strong> \n- Spread {supress_notation(spread, 2)} \n- Upward trend - https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"

                if close_price < float(all_time_low):
                    msg = f"- Candlesick jump and all time high <strong>{symbol}</strong> \n- Spread {supress_notation(spread, 2)} \n- Upward trend - https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"

                if msg:
                    _send_msg(msg)

            # last_processed_kline[symbol] = time.time()
            # If more than half an hour (interval = 30m) has passed
            # Then we should resume sending signals for given symbol
            # if (float(time.time()) - float(last_processed_kline[symbol])) > 400:
            #     del last_processed_kline[symbol]


if __name__ == "__main__":
    start_stream()
