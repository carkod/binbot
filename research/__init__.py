import json
import threading
from time import sleep, time

import requests
from dotenv import load_dotenv
from websocket import WebSocketApp

from apis import BinbotApi
from autotrade import Autotrade
from telegram_bot import TelegramBot
from utils import handle_binance_errors, supress_notation

load_dotenv()


class ResearchSignals(BinbotApi):
    def __init__(self):
        self.interval = "1h"
        self.markets_streams = None
        self.last_processed_kline = {}
        self.skipped_fiat_currencies = [
            "USD",
            "DOWN",
            "EUR",
            "AUD",
            "TRY",
            "BRL",
            "RUB",
        ]  # on top of blacklist
        # This blacklist is necessary to keep prod and local DB synched
        self.telegram_bot = TelegramBot()
        self.max_request = 950  # Avoid HTTP 411 error by separating streams

        # Dynamic data
        response = requests.get(url=f"{self.bb_controller_url}")
        self.settings = response.json()["data"]

        blacklist_res = requests.get(url=f"{self.bb_blacklist_url}")
        self.blacklist_data = handle_binance_errors(blacklist_res)["data"]

        if self.settings:
            self.interval = self.settings["candlestick_interval"]

    def blacklist_coin(self, pair, msg):
        res = requests.post(
            url=self.bb_blacklist_url, json={"pair": pair, "reason": msg}
        )
        result = handle_binance_errors(res)
        return result

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
        url = f"{self.WS_BASE}{string_params}"
        ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.on_close,
            on_message=self.on_message,
        )
        worker_thread = threading.Thread(
            name=f"market_updates_{index}",
            target=ws.run_forever,
            kwargs={"ping_interval": 60},
        )
        worker_thread.start()

    def start_stream(self, previous_ws=None):
        if previous_ws:
            previous_ws.close()
        raw_symbols = self._ticker_price()
        black_list = [x["pair"] for x in self.blacklist_data]
        markets = set([item["symbol"] for item in raw_symbols])
        subtract_list = set(black_list)
        list_markets = markets - subtract_list

        params = []
        for market in list_markets:
            params.append(f"{market.lower()}@kline_{self.interval}")

        stream_1 = params[: self.max_request]
        stream_2 = params[(self.max_request + 1):]

        self._run_streams(stream_1, 1)
        self._run_streams(stream_2, 2)

    def post_error(self, msg):
        res = requests.put(url=self.bb_controller_url, json={"system_logs": msg})
        handle_binance_errors(res)
        return

    def on_close(self, ws, close_status_code, close_msg):
        """
        Library bug not working
        https://github.com/websocket-client/websocket-client/issues/612
        """

        print("Active socket closed", close_status_code, close_msg)

    def on_open(self, ws):
        print("Market data updates socket opened")

    def on_error(self, ws, error):
        msg = f'Research Websocket error: {error}. {"Symbol: " + self.symbol if self.symbol else ""  }'
        print(msg)
        self.post_error(msg)
        # Network error, restart
        if error.args[0] == "Connection to remote host was lost.":
            print("Restarting in 30 seconds...")
            self.post_error(
                "Connection to remote host was lost. Restarting in 30 seconds..."
            )
            sleep(30)
            self.start_stream()

    def on_message(self, ws, message):
        json_response = json.loads(message)
        response = json_response["data"]

        if "result" in json_response and json_response["result"]:
            print(f'Subscriptions: {json_response["result"]}')

        elif "e" in response and response["e"] == "kline":
            self.process_kline_stream(response, ws)

        else:
            print(f"Error: {response}")

    def process_kline_stream(self, result, ws):
        """
        Updates market data in DB for research
        """
        # Check if closed result["k"]["x"]
        if "k" in result and "s" in result["k"]:
            # Check if streams need to be restarted
            close_price = float(result["k"]["c"])
            open_price = float(result["k"]["o"])
            symbol = result["k"]["s"]
            self.symbol = symbol
            data = self._get_candlestick(symbol, self.interval, stats=True)
            if len(data["trace"][1]["y"]) <= 100:
                msg = f"Not enough data to do research on {symbol}"
                print(msg)
                self.blacklist_coin(symbol, msg)
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

            if symbol not in self.last_processed_kline:
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
                    float(close_price) > float(open_price)
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
                    research_controller_res = requests.get(url=self.bb_controller_url)
                    self.settings = handle_binance_errors(research_controller_res)[
                        "data"
                    ]
                    # If dashboard has changed any self.settings
                    # Need to reload websocket
                    if (
                        "update_required" in self.settings
                        and self.settings["update_required"]
                    ):
                        self.settings["update_required"] = False
                        research_controller_res = requests.put(
                            url=self.bb_controller_url, json=self.settings
                        )
                        self.post_error(
                            handle_binance_errors(research_controller_res)["message"]
                        )
                        self.start_stream(previous_ws=ws)
                        return

                    # if autrotrade enabled and it's not an already active bot
                    # this avoids running too many useless bots
                    bots_res = requests.get(
                        url=self.bb_bot_url, params={"status": "active"}
                    )
                    active_bots = handle_binance_errors(bots_res)["data"]
                    active_symbols = [bot["pair"] for bot in active_bots]

                    # Check balance to avoid failed autotrades
                    check_balance_res = requests.get(url=self.bb_balance_estimate_url)
                    balances = handle_binance_errors(check_balance_res)
                    balance_check = int(balances["data"]["estimated_total_gbp"])

                    if (
                        int(self.settings["autotrade"]) == 1
                        and symbol not in active_symbols
                        and balance_check > 0
                    ):
                        autotrade = Autotrade(symbol, self.settings)
                        worker_thread = threading.Thread(
                            name="autotrade_thread", target=autotrade.run
                        )
                        worker_thread.start()

                if msg:
                    self._send_msg(msg)

                self.last_processed_kline[symbol] = time()
                # If more than half an hour (interval = 30m) has passed
                # Then we should resume sending signals for given symbol
                if (float(time()) - float(self.last_processed_kline[symbol])) > 120:
                    del self.last_processed_kline[symbol]


if __name__ == "__main__":
    rs = ResearchSignals()
    rs.start_stream()
