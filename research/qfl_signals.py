import json
import os
import re
import threading
import requests
import logging
import numpy
from signals import SetupSignals
from websocket import WebSocketApp
from decimal import Decimal
from autotrade import process_autotrade_restrictions
from utils import round_numbers
from time import time

class QFL_signals(SetupSignals):
    def __init__(self):
        super().__init__()
        self.exchanges = ["Binance"]
        self.quotes = ["USDT", "BUSD", "USD", "BTC", "ETH"]
        self.hodloo_uri = "wss://alpha2.hodloo.com/ws"
        self.hodloo_chart_url = "https://qft.hodloo.com/#/"
        self.last_processed_asset = {}
        self.blacklist = []

    def custom_telegram_msg(self, msg, symbol):
        message = f"- [{os.getenv('ENV')}] <strong>#QFL Hodloo</strong> signal algorithm #{symbol} {msg} \n- <a href='https://www.binance.com/en/trade/{symbol}'>Binance</a>  \n- <a href='http://terminal.binbot.in/admin/bots/new/{symbol}'>Dashboard trade</a>"

        self._send_msg(message)
        return

    def on_close(self, *args):
        """
        Library bug not working
        https://github.com/websocket-client/websocket-client/issues/612
        """
        logging.info("Active socket closed")

    def on_open(self, *args, **kwargs):
        self.load_data()
        self.blacklist = [item["pair"] for item in self.blacklist_data]
        

    def on_error(self, ws, error):
        msg = f'QFL signals Websocket error: {error}. {"Symbol: " + self.symbol if hasattr(self, "symbol") else ""  }'
        logging.info(msg)
        # API restart 30 secs + 15
        logging.info("Restarting websockets...")
        self.terminate_websockets()
        self.start_stream(ws)
    
    def check_asset(self, asset, ws):
        # Check if pair works with USDT, is availabee in the binance
        request_crypto = requests.get(f"https://min-api.cryptocompare.com/data/v4/all/exchanges?fsym={asset}&e=Binance").json()
        logging.info(f'Checking {asset} existence in Binance...')
        # Cause it to throw error
        request_crypto["Data"]["exchanges"]["Binance"]["pairs"][asset]

        symbol = asset + "USDT"
        return symbol
    
    def get_stats(self, symbol):
        """
        Get standard deviation and lowest price
        """

        data = self._get_candlestick(symbol, "15m")
        if "error" in data and data["error"] == 1:
                return

        list_prices = numpy.array(data["trace"][0]["close"])
        sd = round_numbers((numpy.std(list_prices.astype(numpy.float))), 2)
        lowest_price = numpy.min(numpy.array(data["trace"][0]["close"]).astype(numpy.float))
        return sd, lowest_price

    def on_message(self, ws, payload):
        response = json.loads(payload)
        if response["type"] in ["base-break", "panic"]:
            exchange_str, pair = response["marketInfo"]["ticker"].split(":")
            is_leveraged_token = bool(re.search("UP/", pair)) or bool(
                re.search("DOWN/", pair)
            )
            asset, quote = pair.split("-")
            symbol = pair.replace("-","")
            if not is_leveraged_token and asset not in self.last_processed_asset and symbol not in self.blacklist:

                hodloo_url = f"{self.hodloo_chart_url + exchange_str}:{pair}"
                volume24 = response["marketInfo"]["volume24"]
                alert_price = float(response["marketInfo"]["price"])

                try:
                    self.check_asset(asset, ws)
                except Exception:
                    return
                
                # Because signals for other market could influence also USDT market
                trading_pair = asset + "USDT"

                if response["type"] == "base-break":
                    message = f"\nAlert Price: {alert_price}\n- Base Price:{response['basePrice']} \n- Volume: {volume24}\n- <a href='{hodloo_url}'>Hodloo</a> \n- Running autotrade"
                    sd, lowest_price = self.get_stats(trading_pair)
                    process_autotrade_restrictions(self, trading_pair, ws, "hodloo_qfl_signals_base-break", **{"sd": sd, "current_price": alert_price, "lowest_price": lowest_price})

                    self.custom_telegram_msg(
                        f"[{response['type']}] {'Below ' + str(response['belowBasePct']) + '%' + message if 'belowBasePct' in response else message} -\n lowest price: {lowest_price}", symbol=trading_pair
                    )

                # Uncomment when short_buy strategy is ready
                if response["type"] == "panic":
                    strength = response["strength"]
                    message = f'\nAlert Price: {alert_price}, Volume: {volume24}, Strength: {strength}\n- <a href="{hodloo_url}">Hodloo</a>'
                    sd, lowest_price = self.get_stats(trading_pair)
                    process_autotrade_restrictions(self, trading_pair, ws, "hodloo_qfl_signals_panic", **{"sd": sd, "current_price": alert_price, "lowest_price": lowest_price, "trend": "downtrend"})

                    self.custom_telegram_msg(
                        f"[{response['type']}] {'Below ' + str(response['belowBasePct']) + '%' + message if 'belowBasePct' in response else message} -\n lowest price: {lowest_price}", symbol=trading_pair
                    )

                # Avoid repeating signals with same coin
                self.last_processed_asset[asset] = time()


            if asset in self.last_processed_asset and (float(time()) - float(self.last_processed_asset[asset])) > 3600:
                del self.last_processed_asset[asset]
        return

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

