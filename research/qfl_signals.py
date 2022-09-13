from datetime import datetime
import json
import os
import re
import threading
from telegram_bot import TelegramBot
from websocket import WebSocketApp
from decimal import Decimal

class QFL_signals():
    def __init__(self):
        self.telegram_bot = TelegramBot()
        self.exchanges = ["Binance"]
        self.quotes = ["USDT"]
        self.hodloo_uri = "wss://alpha2.hodloo.com/ws"
        self.hodloo_chart_url = "https://qft.hodloo.com/#/"

    def _restart_websockets(self):
        """
        Restart websockets threads after list of active bots altered
        """
        print("Starting thread cleanup")
        global stop_threads
        stop_threads = True
        # Notify market updates websockets to update
        for thread in threading.enumerate():
            if hasattr(thread, "tag") and thread.name == "qfl_signals" and hasattr(thread, "_target"):
                stop_threads = False
                print("closing QFL websockets thread", thread)
                thread._target.__self__.close()

        pass

    def _send_msg(self, msg, symbol):
        """
        Send message with telegram bot
        To avoid Conflict - duplicate Bot error
        /t command will still be available in telegram bot
        """
        if not hasattr(self.telegram_bot, "updater"):
            self.telegram_bot.run_bot()

        message = f"- [{os.getenv('ENV')}] <strong>#QFL Hodloo</strong> signal algorithm #{symbol} \n - {msg} \n- https://www.binance.com/en/trade/{symbol} \n- Dashboard trade http://terminal.binbot.in/admin/bots/new/{symbol}"

        self.telegram_bot.send_msg(message)
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
        print("Restarting in 45 seconds...")
        self._restart_websockets()
        self.start_stream(ws)

    def on_message(self, ws, payload):
        response = json.loads(payload)
        if response['type'] in ['base-break','panic']:
            exchange_str,pair = response["marketInfo"]["ticker"].split(':')
            is_leveraged_token = bool(re.search('UP/', pair)) or bool(re.search('DOWN/', pair))
            if exchange_str in self.exchanges and not is_leveraged_token:
                hodloo_url = f"{self.hodloo_chart_url + exchange_str}:{pair}"
                asset, quote = pair.split('-')
                pair = pair.replace('-','')
                self._send_msg(f"Check QFL Hodloo signal: {hodloo_url}", pair)
                volume24 = response["marketInfo"]["volume24"]
                if quote in self.quotes:
                    alert_price = Decimal(str(response["marketInfo"]["price"]))

                    if response['type'] == 'base-break':
                        base_price = Decimal(str(response["basePrice"]))
                        message = f'\n[ {datetime.now().replace(microsecond=0)} | {exchange_str} | Base Break ]\n\nSymbol: *{pair}*\nAlert Price: {alert_price} - Base Price: {base_price} - Volume: {volume24}\n[TradingView]({tv_url}) - [Hodloo]({hodloo_url})'
                        
                        if response["belowBasePct"] == 5:
                            print(f"{datetime.now().replace(microsecond=0)} - Processing {pair} for Exchange {exchange_str}")
                            self._send_msg(f"QFL signal %5 alerts: {message}", symbol=pair)

                        if response["belowBasePct"] == 10:
                            print(f"{datetime.now().replace(microsecond=0)} - Processing {pair} for Exchange {exchange_str}")
                            self._send_msg(f"%20 alerts: {message}", symbol=pair)
                    
                    if response['type'] == 'panic':
                        print(f"{datetime.now().replace(microsecond=0)} - Processing {pair} for Exchange {exchange_str}")
                        strength = response["strength"]
                        velocity = response["velocity"]
                        message = f'\n[ {datetime.now().replace(microsecond=0)} | {exchange_str} | Panic Alert ]\n\nSymbol: *{pair}*\nAlert Price: {alert_price}\nVolume: {volume24}\nVelocity: {velocity}\nStrength: {strength}\n[TradingView]({tv_url}) - [Hodloo]({hodloo_url})'
                        self._send_msg(f"Panic alert: {message}", symbol=pair)


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
            name=f"qfl_signals",
            target=ws.run_forever,
            kwargs={"ping_interval": 60},
        )
        worker_thread.tag = "qfl_signals"
        worker_thread.start()
