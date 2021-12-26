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
from datetime import datetime

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
        self.telegram_bot = TelegramBot()
        self.max_request = 950  # Avoid HTTP 411 error by separating streams

    def blacklist_coin(self, pair, msg):
        res = requests.post(
            url=self.bb_blacklist_url, json={"pair": pair, "reason": msg}
        )
        result = handle_binance_errors(res)
        return result

    def load_data(self):
        """
        Load controller data

        - Global settings for autotrade
        - Updated blacklist
        """
        print("Loading controller and blacklist data...")
        settings_res = requests.get(url=f"{self.bb_controller_url}")
        settings_data = handle_binance_errors(settings_res)
        blacklist_res = requests.get(url=f"{self.bb_blacklist_url}")
        blacklist_data = handle_binance_errors(blacklist_res)

        # Show webscket errors
        if "error" in (settings_data, blacklist_res) and (
            settings_data["error"] == 1 or blacklist_res["error"] == 1
        ):
            print(settings_data)

        # Remove restart flag, as we are already restarting
        if (
            "update_required" not in settings_data
            or settings_data["data"]["update_required"]
        ):
            settings_data["data"]["update_required"] = False
            research_controller_res = requests.put(
                url=self.bb_controller_url, json=settings_data
            )
            handle_binance_errors(research_controller_res)

        # Logic for autotrade
        research_controller_res = requests.get(url=self.bb_controller_url)
        research_controller = handle_binance_errors(research_controller_res)
        self.settings = research_controller["data"]

        self.settings = settings_data["data"]
        self.blacklist_data = blacklist_data["data"]
        self.interval = self.settings["candlestick_interval"]
        self.max_request = int(self.settings["max_request"])
        pass

    def new_tokens(self, projects) -> list:
        check_new_coin = (
            lambda coin_trade_time: (
                datetime.now() - datetime.fromtimestamp(coin_trade_time)
            ).days
            < 1
        )

        new_pairs = [
            item["rebaseCoin"] + item["asset"]
            for item in projects["data"]["completed"]["list"]
            if check_new_coin(int(item["coinTradeTime"]) / 1000)
        ]

        return new_pairs

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

        self.load_data()
        raw_symbols = self.ticker_price()
        black_list = [x["pair"] for x in self.blacklist_data]
        markets = set([item["symbol"] for item in raw_symbols])
        subtract_list = set(black_list)
        list_markets = markets - subtract_list
        # Optimal setting below setting greatly reduces the websocket load
        # To make it faster to scan and reduce chances of being blocked by Binance
        if self.settings and self.settings["balance_to_use"] != "GBP":
            list_markets = [
                item for item in list_markets if self.settings["balance_to_use"] in item
            ]

        params = []
        for market in list_markets:
            params.append(f"{market.lower()}@kline_{self.interval}")

        stream_1 = params[: self.max_request]
        self._run_streams(stream_1, 1)

        if len(params) > self.max_request:
            stream_2 = params[(self.max_request + 1) :]
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
        print("Active socket closed")

    def on_open(self, ws):
        print("Research signals websocket opened")

    def on_error(self, ws, error):
        msg = f'Research Websocket error: {error}. {"Symbol: " + self.symbol if hasattr(self, "symbol") else ""  }'
        print(msg)
        print("Restarting in 45 seconds...")
        # API restart 30 secs + 15
        sleep(45)
        self.start_stream(ws)

    def on_message(self, ws, message):
        json_response = json.loads(message)
        response = json_response["data"]

        if "result" in json_response and json_response["result"]:
            print(f'Subscriptions: {json_response["result"]}')

        elif "e" in response and response["e"] == "kline":
            self.process_kline_stream(response, ws)

    def process_kline_stream(self, result, ws):
        """
        Updates market data in DB for research
        """
        # Sleep 1 hour because of snapshot account request weight
        if datetime.now().time().hour == 0 and datetime.now().time().minute == 0:
            sleep(3600)

        # if autrotrade enabled and it's not an already active bot
        # this avoids running too many useless bots
        # Temporarily restricting to 1 bot for low funds
        bots_res = requests.get(
            url=self.bb_bot_url, params={"status": "active"}
        )
        active_bots = handle_binance_errors(bots_res)["data"]
        active_symbols = [bot["pair"] for bot in active_bots]

        if "k" in result and "s" in result["k"] and len(active_symbols) == 0:
            close_price = float(result["k"]["c"])
            open_price = float(result["k"]["o"])
            symbol = result["k"]["s"]
            ws.symbol = symbol
            print(f"Signal {symbol}")
            data = self._get_candlestick(symbol, self.interval, stats=True)
            if not data or len(data["trace"][1]["y"]) <= 100:
                msg = f"Not enough data to do research on {symbol}"
                print(msg)
                self.blacklist_coin(symbol, msg)

            ma_100 = data["trace"][1]["y"]
            ma_25 = data["trace"][2]["y"]
            ma_7 = data["trace"][3]["y"]
            # Average amplitude
            amplitude = float(data["amplitude"])
            msg = None

            if symbol not in self.last_processed_kline:
                if (
                    # It doesn't have to be a red candle for upward trending
                    float(close_price) > float(open_price)
                    and amplitude > 0.02
                    and close_price > ma_7[len(ma_7) - 1]
                    and open_price > ma_7[len(ma_7) - 1]
                    and close_price > ma_7[len(ma_7) - 2]
                    and open_price > ma_7[len(ma_7) - 2]
                    and close_price > ma_7[len(ma_7) - 3]
                    and open_price > ma_7[len(ma_7) - 3]
                    and close_price > ma_7[len(ma_7) - 4]
                    and open_price > ma_7[len(ma_7) - 4]
                    and close_price > ma_7[len(ma_7) - 5]
                    and open_price > ma_7[len(ma_7) - 5]
                    and close_price > ma_100[len(ma_100) - 1]
                    and open_price > ma_100[len(ma_100) - 1]
                    and close_price > ma_25[len(ma_25) - 1]
                    and open_price > ma_25[len(ma_25) - 1]
                    and close_price > ma_25[len(ma_25) - 2]
                    and open_price > ma_25[len(ma_25) - 2]
                    and close_price > ma_25[len(ma_25) - 3]
                    and open_price > ma_25[len(ma_25) - 3]
                    and close_price > ma_25[len(ma_25) - 4]
                    and open_price > ma_25[len(ma_25) - 4]
                ):
                    msg = f"- Candlesick <strong>strong upward trend</strong> {symbol} \n- Amplitude {supress_notation(amplitude, 2)} \n- https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://binbot.in/admin/bots-create"
                    self._send_msg(msg)
                    print(msg)

                    # Check balance to avoid failed autotrades
                    check_balance_res = requests.get(url=self.bb_balance_estimate_url)
                    balances = handle_binance_errors(check_balance_res)
                    if "error" in balances and balances["error"] == 1:
                        print(balances["message"])
                        return

                    balance_check = int(balances["data"]["total_fiat"])

                    # If dashboard has changed any self.settings
                    # Need to reload websocket
                    if (
                        "update_required" in self.settings
                        and self.settings["update_required"]
                    ):
                        print("Update required, restart stream")
                        self.start_stream(previous_ws=ws)
                        pass

                    if (
                        int(self.settings["autotrade"]) == 1
                        # Temporary restriction for few funds
                        and balance_check > 0
                    ):
                        autotrade = Autotrade(symbol, self.settings, amplitude)
                        autotrade.run()

                self.last_processed_kline[symbol] = time()

            # If more than half an hour (interval = 30m) has passed
            # Then we should resume sending signals for given symbol
            if (float(time()) - float(self.last_processed_kline[symbol])) > 1200:
                del self.last_processed_kline[symbol]
