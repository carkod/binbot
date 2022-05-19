import json
import random
import threading
from datetime import datetime
from time import sleep, time

import requests
from websocket import WebSocketApp

from algorithms.candlejump_sd import candlejump_sd
from algorithms.candlestick_patterns import candlestick_patterns
from algorithms.ma_candlestick_jump import ma_candlestick_jump
from apis import BinbotApi
from autotrade import Autotrade
from pattern_detection import chaikin_oscillator, linear_regression, stdev
from telegram_bot import TelegramBot
from test_autotrade import TestAutotrade
from utils import handle_binance_errors


class ResearchSignals(BinbotApi):
    def __init__(self):
        self.interval = "15m"
        self.markets_streams = None
        self.last_processed_kline = {}
        self.skipped_fiat_currencies = [
            "DOWN",
            "UP",
            "AUD",
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
                url=self.bb_controller_url, json=settings_data["data"]
            )
            handle_binance_errors(research_controller_res)

        # Logic for autotrade
        research_controller_res = requests.get(url=self.bb_controller_url)
        research_controller = handle_binance_errors(research_controller_res)
        self.settings = research_controller["data"]

        test_autotrade_settings = requests.get(url=f"{self.bb_test_autotrade_url}")
        test_autotrade = handle_binance_errors(test_autotrade_settings)
        self.test_autotrade_settings = test_autotrade["data"]

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

        for s in raw_symbols:
            for pair in self.skipped_fiat_currencies:
                if pair in s["symbol"]:
                    self.blacklist_coin(
                        s["symbol"], "Value too high, can't buy enough coins to earn."
                    )

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

    def run_autotrade(self, symbol, ws, algorithm, test_only=False, *args, **kwargs):
        """
        Refactored autotrade conditions.
        Previously part of process_kline_stream
        1. Checks if we have balance to trade
        2.
        """
        # Check balance to avoid failed autotrades
        check_balance_res = requests.get(url=self.bb_balance_estimate_url)
        balances = handle_binance_errors(check_balance_res)
        if "error" in balances and balances["error"] == 1:
            print(balances["message"])
            return

        balance_check = int(balances["data"]["total_fiat"])

        # If dashboard has changed any self.settings
        # Need to reload websocket
        if "update_required" in self.settings and self.settings["update_required"]:
            print("Update required, restart stream")
            self.start_stream(previous_ws=ws)
            pass
        
        if (
            int(self.settings["autotrade"]) == 1
            # Temporary restriction for few funds
            and balance_check > 0
            and not test_only
        ):
            autotrade = Autotrade(symbol, self.settings, algorithm)
            autotrade.run()

        # Execute test_autrade after autotrade to avoid test_autotrade bugs stopping autotrade
        # test_autotrade may execute same bots as autotrade, for the sake of A/B testing
        # the downfall is that it can increase load for the server if there are multiple bots opened
        # e.g. autotrade bots not updating can be a symptom of this
        paper_trading_bots_res = requests.get(url=self.bb_test_bot_url, params={"status": "active"})
        paper_trading_bots = handle_binance_errors(paper_trading_bots_res)
        active_test_bots = [item["pair"] for item in paper_trading_bots["data"]]
        if symbol not in active_test_bots and int(self.test_autotrade_settings["test_autotrade"]) == 1:
            # Test autotrade runs independently of autotrade = 1
            test_autotrade = TestAutotrade(symbol, self.test_autotrade_settings, algorithm, args)
            test_autotrade.run()

    def on_close(self, *args):
        """
        Library bug not working
        https://github.com/websocket-client/websocket-client/issues/612
        """
        print("Active socket closed")

    def on_open(self, *args, **kwargs):
        print("Research signals websocket opened")

    def on_error(self, ws, error):
        msg = f'Research Websocket error: {error}. {"Symbol: " + self.symbol if hasattr(self, "symbol") else ""  }'
        print(msg)
        # API restart 30 secs + 15
        print("Restarting in 45 seconds...")
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
        bots_res = requests.get(url=self.bb_bot_url, params={"status": "active"})
        active_bots = handle_binance_errors(bots_res)["data"]
        active_symbols = [bot["pair"] for bot in active_bots]

        if "k" in result and "s" in result["k"] and len(active_symbols) == 0:
            close_price = float(result["k"]["c"])
            open_price = float(result["k"]["o"])
            symbol = result["k"]["s"]
            ws.symbol = symbol
            data = self._get_candlestick(symbol, self.interval, stats=True)

            if len(data["trace"][0]["x"]) > 1:
                # Update klines database
                payload = {
                    "data": result["k"],
                    "symbol": result["k"]["s"],
                    "interval": self.interval,
                }
                klines_res = requests.put(url=self.bb_klines, json=payload)
                # Not handling binance errors to avoid cluttering the log

            ma_100 = data["trace"][1]["y"]
            ma_25 = data["trace"][2]["y"]
            ma_7 = data["trace"][3]["y"]

            if len(ma_100) == 0:
                msg = f"Not enough data to do research on {symbol}"
                print(msg)
                if random.randint(0, 20) == 15:
                    print("Cleaning db of incomplete data...")
                    delete_klines_res = requests.delete(
                        url=self.bb_klines, params={"symbol": symbol}
                    )
                    result = handle_binance_errors(delete_klines_res)
                return

            # Average amplitude
            msg = None

            if symbol not in self.last_processed_kline:
                value, chaikin_diff = chaikin_oscillator(
                    data["trace"][0], data["volumes"]
                )
                slope, intercept = linear_regression(data["trace"][0])
                sd = stdev(data["trace"][0])

                reg_equation = f"{slope}X + {intercept}"

                # Looking at graphs, sd > 0.006 tend to give at least 3% up and down movement
                candlestick_patterns(
                    data["trace"][0],
                    sd,
                    close_price,
                    open_price,
                    value,
                    chaikin_diff,
                    reg_equation,
                    self._send_msg,
                    self.run_autotrade,
                    symbol,
                    ws,
                    intercept,
                    ma_25
                )

                ma_candlestick_jump(
                    close_price,
                    open_price,
                    ma_7,
                    ma_100,
                    ma_25,
                    symbol,
                    sd,
                    value,
                    chaikin_diff,
                    reg_equation,
                    self._send_msg,
                    self.run_autotrade,
                    ws,
                    intercept,
                )

                candlejump_sd(
                    close_price,
                    open_price,
                    ma_7,
                    ma_100,
                    ma_25,
                    symbol,
                    sd,
                    value,
                    chaikin_diff,
                    reg_equation,
                    self._send_msg,
                    self.run_autotrade,
                    ws,
                    intercept,
                )

                self.last_processed_kline[symbol] = time()

            # If more than 6 hours passed has passed
            # Then we should resume sending signals for given symbol
            if (float(time()) - float(self.last_processed_kline[symbol])) > 10000:
                del self.last_processed_kline[symbol]
        pass
