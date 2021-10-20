import json
import os
import threading
from time import sleep, time

import pandas
import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from websocket import WebSocketApp

from apis import BinbotApi
from autotrade import Autotrade
from telegram_bot import TelegramBot
from utils import handle_binance_errors, supress_notation

load_dotenv()

mongo = MongoClient(
    os.environ["MONGO_HOSTNAME"],
    int(os.environ["MONGO_PORT"]),
    username=os.environ["MONGO_AUTH_USERNAME"],
    password=os.environ["MONGO_AUTH_PASSWORD"],
    authSource=os.environ["MONGO_AUTH_DATABASE"],
)
db = mongo["binbot"]
interval = "1h"
list_markets = []
markets_streams = None
last_processed_kline = {}
skipped_fiat_currencies = ["USD", "DOWN", "EUR", "AUD", "TRY", "BRL", "RUB"] # on top of blacklist
# This blacklist is necessary to keep prod and local DB synched
telegram_bot = TelegramBot()
max_request = 950  # Avoid HTTP 411 error by separating streams
binbot_api = BinbotApi()

# Dynamic data
settings = db.research_controller.find_one({"_id": "settings"})


if settings:
    interval = settings["candlestick_interval"]

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


def _run_streams(stream, index):
    string_params = "/".join(stream)
    url = f"{binbot_api.WS_BASE}{string_params}"
    ws = WebSocketApp(
        url,
        on_open=on_open,
        on_error=on_error,
        on_close=on_close,
        on_message=on_message,
    )
    worker_thread = threading.Thread(
        name=f"market_updates_{index}",
        target=ws.run_forever,
        kwargs={"ping_interval": 60},
    )
    worker_thread.start()


def start_stream(previous_ws=None):
    if previous_ws:
        previous_ws.close()
    raw_symbols = binbot_api._ticker_price()
    blacklist_data = list(db.blacklist.find())
    black_list = [x["pair"] for x in blacklist_data]
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

def post_error(msg):
    res = requests.put(url=binbot_api.bb_controller_url, json={"system_logs": msg })
    result = handle_binance_errors(res)
    return


def on_close(ws, close_status_code, close_msg):
    """
    Library bug not working
    https://github.com/websocket-client/websocket-client/issues/612
    """
    
    print("Active socket closed", close_status_code, close_msg)
    # Controlled close stream
    # There is no reason to keep it permanently closed
    # unless there is an error, which will be handled `on_error`
    start_stream()


def on_open(ws):
    print("Market data updates socket opened")


def on_error(ws, error):
    msg = f"Research Websocket error: {error}. Symbol: {ws.symbol}"
    print(msg)
    post_error(msg)
    # Network error, restart
    if error.args[0] == "Connection to remote host was lost.":
        print("Restarting in 30 seconds...")
        post_error("Connection to remote host was lost. Restarting in 30 seconds...")
        sleep(30)
        start_stream()


def on_message(ws, message):
    json_response = json.loads(message)
    response = json_response["data"]

    if "result" in json_response and json_response["result"]:
        print(f'Subscriptions: {json_response["result"]}')

    elif "e" in response and response["e"] == "kline":
        process_kline_stream(response, ws)

    else:
        print(f"Error: {response}")

def blacklist_coin(pair, msg):
    res = requests.post(url=binbot_api.bb_blacklist_url, json={"pair": pair, "reason": msg })
    result = handle_binance_errors(res)
    return result


def process_kline_stream(result, ws):
    """
    Updates market data in DB for research
    """
    # Check if closed result["k"]["x"]
    if "k" in result and "s" in result["k"]:
        # Check if streams need to be restarted
        close_price = float(result["k"]["c"])
        open_price = float(result["k"]["o"])
        symbol = result["k"]["s"]
        ws.symbol = symbol
        data = binbot_api._get_candlestick(symbol, interval, stats=True)
        if len(data["trace"][1]["y"]) <= 100:
            msg = f"Not enough data to do research on {symbol}"
            print(msg)
            blacklist_coin(symbol, msg)
            return

        ma_100 = data["trace"][1]["y"]
        ma_25 = data["trace"][2]["y"]
        ma_7 = data["trace"][3]["y"]
        curr_candle_spread = float(data["curr_candle_spread"])
        curr_volume_spread = float(data["curr_volume_spread"])
        avg_candle_spread = float(data["avg_candle_spread"])
        avg_volume_spread = float(data["avg_volume_spread"])
        amplitude = float(data["amplitude"])
        all_time_low = float(data["all_time_low"])

        msg = None

        if symbol not in last_processed_kline:
            if (
                float(close_price) > float(open_price)
                and (
                    curr_candle_spread > (avg_candle_spread * 2)
                    and curr_volume_spread > avg_volume_spread
                )
                and (close_price > ma_100[len(ma_100) - 1])
                and amplitude > 0.1
            ):
                # Send Telegram
                msg = f"- Candlesick <strong>jump</strong> {symbol} \n- Amplitude {supress_notation(amplitude, 2)} \n- Upward trend - https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"

                if close_price < float(all_time_low):
                    msg = f"- Candlesick jump and all time high <strong>{symbol}</strong> \n- Amplitude {supress_notation(amplitude, 2)} \n- Upward trend - https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"

            if (
                # BRL cannot be transformed by coinbase
                not any([x in symbol for x in ["USD", "DOWN", "EUR", "AUD", "TRY", "BRL", "RUB"]])
                and float(close_price) > float(open_price)
                # and spread > 0.1
                and (
                    close_price > ma_7[len(ma_7) - 1]
                    and open_price > ma_7[len(ma_7) - 1]
                )
                and (
                    close_price > ma_7[len(ma_7) - 2]
                    and open_price > ma_7[len(ma_7) - 2]
                )
                and (
                    close_price > ma_7[len(ma_7) - 3]
                    and open_price > ma_7[len(ma_7) - 3]
                )
                and (
                    close_price > ma_7[len(ma_7) - 4]
                    and open_price > ma_7[len(ma_7) - 4]
                )
                and (
                    close_price > ma_7[len(ma_7) - 5]
                    and open_price > ma_7[len(ma_7) - 5]
                )
                and (
                    close_price > ma_100[len(ma_100) - 1]
                    and open_price > ma_100[len(ma_100) - 1]
                )
                and (
                    close_price > ma_25[len(ma_25) - 1]
                    and open_price > ma_25[len(ma_25) - 1]
                )
                and (
                    close_price > ma_25[len(ma_25) - 2]
                    and open_price > ma_25[len(ma_25) - 2]
                )
                and (
                    close_price > ma_25[len(ma_25) - 3]
                    and open_price > ma_25[len(ma_25) - 3]
                )
                and (
                    close_price > ma_25[len(ma_25) - 4]
                    and open_price > ma_25[len(ma_25) - 4]
                )
                and (
                    close_price > ma_25[len(ma_25) - 5]
                    and open_price > ma_25[len(ma_25) - 5]
                )
            ):
                msg = f"- Candlesick <strong>strong upward trend</strong> {symbol} \n- Amplitude {supress_notation(amplitude, 2)} \n- https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"

                # Logic for autotrade
                research_controller_res = requests.get(url=binbot_api.bb_controller_url)
                settings = handle_binance_errors(research_controller_res)["data"]
                # If dashboard has changed any settings
                # Need to reload websocket
                if "update_required" in settings and settings["update_required"]:
                    settings["update_required"] = False
                    research_controller_res = requests.put(url=binbot_api.bb_controller_url, json=settings)
                    post_error(handle_binance_errors(research_controller_res)["message"])
                    start_stream(previous_ws=ws)
                    return

                # if autrotrade enabled and it's not an already active bot
                # this avoids running too many useless bots
                bots_res = requests.get(url=binbot_api.bb_controller_url)
                active_bots = handle_binance_errors(bots_res)["data"]

                # Check balance to avoid failed autotrades
                check_balance_res = requests.get(url=binbot_api.bb_balance_estimate_url)
                balances = handle_binance_errors(check_balance_res)
                balance_check = int(balances["data"]["estimated_total_gbp"])

                if int(settings["autotrade"]) == 1 and symbol not in active_bots and balance_check > 0:
                    autotrade = Autotrade(symbol, settings)
                    worker_thread = threading.Thread(
                        name="autotrade_thread", target=autotrade.run
                    )
                    worker_thread.start()

            if msg:
                _send_msg(msg)

            last_processed_kline[symbol] = time()
            # If more than half an hour (interval = 30m) has passed
            # Then we should resume sending signals for given symbol
            if (float(time()) - float(last_processed_kline[symbol])) > 120:
                del last_processed_kline[symbol]


if __name__ == "__main__":
    start_stream()
