import json
import os
import re
import threading
import requests
from signals import SetupSignals
from websocket import WebSocketApp
from decimal import Decimal
from autotrade import Autotrade
from utils import handle_binance_errors


class QFL_signals(SetupSignals):

    def __init__(self):
        super().__init__()
        self.exchanges = ["Binance"]
        self.quotes = ["USDT", "BUSD", "USD", "BTC", "ETH"]
        self.hodloo_uri = "wss://alpha2.hodloo.com/ws"
        self.hodloo_chart_url = "https://qft.hodloo.com/#/"

    def custom_telegram_msg(self, msg, symbol):
        message = f"- [{os.getenv('ENV')}] <strong>#QFL Hodloo</strong> signal algorithm #{symbol} \n - {msg} \n- <a href='https://www.binance.com/en/trade/{symbol}'>Binance</a>  \n- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>"

        self._send_msg(message)
        return

    def on_close(self, *args):
        """
        Library bug not working
        https://github.com/websocket-client/websocket-client/issues/612
        """
        print("Active socket closed")

    def on_open(self, *args, **kwargs):
        print("QFL signals websocket opened")

    def on_error(self, ws, error):
        msg = f'QFL signals Websocket error: {error}. {"Symbol: " + self.symbol if hasattr(self, "symbol") else ""  }'
        print(msg)
        # API restart 30 secs + 15
        print("Restarting...")
        self._restart_websockets()
        self.start_stream(ws)

    def on_message(self, ws, payload):
        response = json.loads(payload)
        if response["type"] in ["base-break", "panic"]:
            exchange_str, pair = response["marketInfo"]["ticker"].split(":")
            is_leveraged_token = bool(re.search("UP/", pair)) or bool(
                re.search("DOWN/", pair)
            )
            # testing
            symbol = pair.replace("-", "")
            asset, quote = pair.split("-")

            # Check if pair works with USDT
            request_crypto = requests.get(f"https://min-api.cryptocompare.com/data/v4/all/exchanges?fsym={asset}&e=Binance").json()
            try:
                request_crypto["Data"]["exchanges"]["Binance"]["pairs"][asset]
            except KeyError:
                return

            test_symbol = asset + "USDT"
            self.run_autotrade(test_symbol, ws, "hodloo_qfl_signals", True)
            return
            # testing ends
            if exchange_str in self.exchanges and not is_leveraged_token:
                hodloo_url = f"{self.hodloo_chart_url + exchange_str}:{symbol}"
                asset, quote = pair.split("-")
                pair = pair.replace("-", "")
                volume24 = response["marketInfo"]["volume24"]
                # if quote in self.quotes:
                alert_price = Decimal(str(response["marketInfo"]["price"]))

                if response["type"] == "base-break":
                    base_price = Decimal(str(response["basePrice"]))
                    message = f"**{pair}**, Alert Price: {alert_price}, Base Price: {base_price}, Volume: {volume24}\n - <a href='{hodloo_url}'>Hodloo</a>"

                    if response["belowBasePct"] == 5:
                        self.custom_telegram_msg(
                            f"Base Break Symbol Below 10%{message}", symbol=pair
                        )
                        self.run_autotrade(pair, ws, "hodloo_qfl_signals", True)

                    if response["belowBasePct"] == 10:
                        self.custom_telegram_msg(
                            f"Base Break Symbol Below 10% {message}", symbol=pair
                        )
                        self.run_autotrade(pair, ws, "hodloo_qfl_signals", True)

                if response["type"] == "panic":
                    strength = response["strength"]
                    velocity = response["velocity"]
                    message = f'[Panic] Symbol: **{pair}**\nAlert Price: {alert_price}\nVolume: {volume24}\nVelocity: {velocity}\nStrength: {strength}\n - <a href="{hodloo_url}">Hodloo</a>'
                    self.custom_telegram_msg(message, symbol=pair)

    def start_stream(self, ws=None):
        if ws:
            ws.close()

        ws = WebSocketApp(
            self.hodloo_uri,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.on_close,
            on_message=self.on_message,
        )

        worker_thread = threading.Thread(
            name="qfl_signals_thread",
            target=ws.run_forever,
            kwargs={"ping_interval": 60},
        )
        worker_thread.tag = "qfl_signals_thread"
        worker_thread.start()

    def run_autotrade(self, symbol, ws, algorithm, test_only=False, *args, **kwargs):
        """
        Refactored autotrade conditions.
        Previously part of process_kline_stream
        1. Checks if we have balance to trade
        2. Check if we need to update websockets
        3. Check if autotrade is enabled
        4. Check if test autotrades
        """
        self.load_data()
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
            autotrade = Autotrade(symbol, self.settings, algorithm, "bots")
            autotrade.activate_autotrade()

        # Execute test_autrade after autotrade to avoid test_autotrade bugs stopping autotrade
        # test_autotrade may execute same bots as autotrade, for the sake of A/B testing
        # the downfall is that it can increase load for the server if there are multiple bots opened
        # e.g. autotrade bots not updating can be a symptom of this
        if (
            symbol not in self.active_test_bots
            and int(self.test_autotrade_settings["test_autotrade"]) == 1
        ):
            # Test autotrade runs independently of autotrade = 1
            test_autotrade = Autotrade(
                symbol, self.test_autotrade_settings, algorithm, "paper_trading"
            )
            test_autotrade.activate_autotrade()