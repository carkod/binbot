import json
import random
import threading
import math
import numpy
from datetime import datetime
from time import sleep, time


import requests
from websocket import WebSocketApp

from algorithms.ma_candlestick_jump import ma_candlestick_jump
from apis import BinbotApi
from autotrade import process_autotrade_restrictions
from telegram_bot import TelegramBot
from utils import handle_binance_errors, round_numbers
from datetime import datetime
from logging import info

class SetupSignals(BinbotApi):
    def __init__(self):
        self.interval = "15m"
        self.markets_streams = None
        self.skipped_fiat_currencies = [
            "DOWN",
            "UP",
            "AUD",
        ]  # on top of blacklist
        self.telegram_bot = TelegramBot()
        self.max_request = 950  # Avoid HTTP 411 error by separating streams
        self.active_symbols = []
        self.thread_ids = []
        self.active_test_bots = []
        self.blacklist_data = []
        self.test_autotrade_settings = {}
        self.settings = {}

    def terminate_websockets(self, thread_name="market_updates"):
        """
        Close websockets through threads
        """
        info("Starting thread cleanup")
        global stop_threads
        stop_threads = True
        # Notify market updates websockets to update
        for thread in threading.enumerate():
            if (
                hasattr(thread, "tag")
                and thread_name in thread.name
                and hasattr(thread, "_target")
            ):
                stop_threads = False
                print(f"Closing websockets {thread._target.__self__} on thread {thread.name}")
                thread._target.__self__.close()

        pass

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
        info("Loading controller and blacklist data...")
        if self.settings and self.test_autotrade_settings:
            info("Settings and Test autotrade settings already loaded, skipping...")
            return

        settings_res = requests.get(url=f"{self.bb_autotrade_settings_url}")
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
                url=self.bb_autotrade_settings_url, json=settings_data["data"]
            )
            handle_binance_errors(research_controller_res)

        # Logic for autotrade
        research_controller_res = requests.get(url=self.bb_autotrade_settings_url)
        research_controller = handle_binance_errors(research_controller_res)
        self.settings = research_controller["data"]

        test_autotrade_settings = requests.get(url=f"{self.bb_test_autotrade_url}")
        test_autotrade = handle_binance_errors(test_autotrade_settings)
        self.test_autotrade_settings = test_autotrade["data"]

        self.settings = settings_data["data"]
        self.blacklist_data = blacklist_data["data"]
        self.interval = self.settings["candlestick_interval"]
        self.max_request = int(self.settings["max_request"])

        # if autrotrade enabled and it's not an already active bot
        # this avoids running too many useless bots
        # Temporarily restricting to 1 bot for low funds
        bots_res = requests.get(
            url=self.bb_bot_url, params={"status": "active", "no_cooldown": True}
        )
        active_bots = handle_binance_errors(bots_res)["data"]
        self.active_symbols = [bot["pair"] for bot in active_bots]

        paper_trading_bots_res = requests.get(
            url=self.bb_test_bot_url, params={"status": "active", "no_cooldown": True}
        )
        paper_trading_bots = handle_binance_errors(paper_trading_bots_res)
        self.active_test_bots = [item["pair"] for item in paper_trading_bots["data"]]
        pass

    def post_error(self, msg):
        res = requests.put(url=self.bb_autotrade_settings_url, json={"system_logs": msg})
        handle_binance_errors(res)
        return

    def reached_max_active_autobots(self, db_collection_name):
        """
        Check max `max_active_autotrade_bots` in controller settings

        Args:
        - db_collection_name [string]: Database collection name ["paper_trading", "bots"]

        If total active bots > settings.max_active_autotrade_bots
        do not open more bots. There are two reasons for this:
        - In the case of test bots, infininately opening bots will open hundreds of bots
        which will drain memory and downgrade server performance
        - In the case of real bots, opening too many bots could drain all funds
        in bots that are actually not useful or not profitable. Some funds
        need to be left for Safety orders
        """
        if db_collection_name == "paper_trading":
            if not self.test_autotrade_settings:
                self.load_data()

            active_bots_res = requests.get(
                url=self.bb_test_bot_url, params={"status": "active"}
            )
            active_bots = handle_binance_errors(active_bots_res)
            active_count = len(active_bots["data"])
            if active_count > self.test_autotrade_settings["max_active_autotrade_bots"]:
                return True

        if db_collection_name == "bots":
            if not self.settings:
                self.load_data()
            active_bots_res = requests.get(
                url=self.bb_bot_url, params={"status": "active"}
            )
            active_bots = handle_binance_errors(active_bots_res)
            active_count = len(active_bots["data"])
            if active_count > self.settings["max_active_autotrade_bots"]:
                return True

        return False


class ResearchSignals(SetupSignals):
    def __init__(self):
        info("Started research signals")
        self.last_processed_kline = {}
        super().__init__()

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
        ws.id = f"signal_updates_socket_{index}"
        worker_thread = threading.Thread(
            name=f"signal_updates{index}",
            target=ws.run_forever
        )
        worker_thread.tag = "signal_updates"
        worker_thread.start()

    def start_stream(self):
        self.load_data()
        raw_symbols = self.ticker_price()
        if not raw_symbols:
            print("No symbols provided by ticket_price", raw_symbols)

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

        total_threads = math.floor(len(list_markets) / self.max_request) + (
            1 if len(list_markets) % self.max_request > 0 else 0
        )
        # It's not possible to have websockets with more 950 pairs
        # So set default to max 950
        stream = params[:950]

        if total_threads > 1 or not self.max_request:
            for index in range(total_threads - 1):
                stream = params[(self.max_request + 1) :]
                if index == 0:
                    stream = params[: self.max_request]
                self._run_streams(stream, index)
        else:
            self._run_streams(stream, 1)

    def on_close(self, *args):
        """
        Library bug not working
        https://github.com/websocket-client/websocket-client/issues/612
        """
        print("Active socket closed")

    def on_open(self, ws, *args, **kwargs):
        print(f"Research signals websocket {ws.id} opened")

    def on_error(self, ws, error):
        msg = f'Research Websocket error: {error}. {"Symbol: " + self.symbol if hasattr(self, "symbol") else ""  }'
        print(msg)
        # API restart 30 secs + 15
        print("Restarting in 45 seconds...")
        sleep(45)

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

        symbol = result["k"]["s"]
        if (
            symbol
            and "k" in result
            and "s" in result["k"]
            and symbol not in self.active_symbols
            and symbol not in self.last_processed_kline
        ):
            close_price = float(result["k"]["c"])
            open_price = float(result["k"]["o"])
            ws.symbol = symbol
            data = self._get_candlestick(symbol, self.interval, stats=True)

            if "error" in data and data["error"] == 1:
                return

            ma_100 = data["trace"][1]["y"]
            ma_25 = data["trace"][2]["y"]
            ma_7 = data["trace"][3]["y"]

            if len(ma_100) == 0:
                msg = f"Not enough ma_100 data: {symbol}"
                info(msg)
                if random.randint(0, 20) == 15:
                    info("Cleaning db of incomplete data...")
                    delete_klines_res = requests.delete(
                        url=self.bb_candlestick_url, params={"symbol": symbol}
                    )
                    result = handle_binance_errors(delete_klines_res)
                    self.last_processed_kline[symbol] = time()
                return

            # Average amplitude
            msg = None
            list_prices = numpy.array(data["trace"][0]["close"])
            sd = round_numbers((numpy.std(list_prices.astype(numpy.float))), 2)

            # historical lowest for short_buy_price
            lowest_price = numpy.min(numpy.array(data["trace"][0]["close"]).astype(numpy.float))
            
            ma_candlestick_jump(
                self,
                close_price,
                open_price,
                ma_7,
                ma_100,
                ma_25,
                symbol,
                sd,
                self._send_msg,
                process_autotrade_restrictions,
                ws,
                lowest_price
            )

            self.last_processed_kline[symbol] = time()

        # If more than 6 hours passed has passed
        # Then we should resume sending signals for given symbol
        if symbol in self.last_processed_kline and (float(time()) - float(self.last_processed_kline[symbol])) > 6000:
            del self.last_processed_kline[symbol]
        pass
