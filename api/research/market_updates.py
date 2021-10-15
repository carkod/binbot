import json
import os

import requests
from api.account.account import Account
from api.app import create_app
from api.deals.deal_updates import DealUpdates
from api.tools.handle_error import handle_error
from websocket import WebSocketApp
from flask import Response, g

class MarketUpdates(Account):
    """
    Further explanation in docs/market_updates.md
    """

    bb_base_url = f'{os.getenv("FLASK_DOMAIN")}'
    bb_candlestick_url = f"{bb_base_url}/charts/candlestick"
    bb_24_ticker_url = f"{bb_base_url}/account/ticker24"
    bb_symbols_raw = f"{bb_base_url}/account/symbols/raw"

    def __init__(self, interval="5m"):
        self.app = create_app()
        self.markets_streams = None
        self.interval = interval

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

    def start_stream(self):
        """
        Start/restart websocket streams
        """
        # Close websocekts before starting
        if self.markets_streams:
            self.markets_streams.close()

        markets = list(self.app.db.bots.distinct("pair", {"status": "active"}))
        params = []
        for market in markets:
            params.append(f"{market.lower()}@kline_{self.interval}")

        string_params = "/".join(params)
        url = f"{self.WS_BASE}{string_params}"
        ws = WebSocketApp(
            url,
            on_open=self.on_open,
            on_error=self.on_error,
            on_close=self.close_stream,
            on_message=self.on_message,
        )
        # This is required to allow the websocket to be closed anywhere in the app
        self.markets_streams = ws
        # Run the websocket with ping intervals to avoid disconnection
        ws.run_forever(ping_interval=70)

    def close_stream(self, ws, close_status_code, close_msg):
        print("Active socket closed", close_status_code, close_msg)

    def on_open(self, ws):
        print("Market data updates socket opened")

    def on_error(self, ws, error):
        error_msg = f'Deal Websocket error: {error}. Symbol: {ws.symbol if hasattr(ws, "symbol") else ""}'
        print(error_msg)
        if error.args[0] == "Connection to remote host was lost.":
            self.start_stream()
        self.app.db.research_controller.find_one_and_update({"_id": "settings"}, {"$push": { "error": error_msg }})

    def on_message(self, ws, message):
        json_response = json.loads(message)

        if "result" in json_response:
            print(f'Subscriptions: {json_response["result"]}')

        if "data" in json_response:
            if "e" in json_response["data"] and json_response["data"]["e"] == "kline":
                self.process_deals(json_response["data"], ws)
            else:
                print(f'Error: {json_response["data"]}')

    def process_deals(self, result, ws):
        """
        Updates deals with klines websockets,
        when price and symbol match existent deal
        """
        if "k" in result:
            close_price = result["k"]["c"]
            symbol = result["k"]["s"]
            ws.symbol = symbol
            # Update Current price
            bot = self.app.db.bots.find_one_and_update(
                {"pair": symbol}, {"$set": {"deal.current_price": close_price}}
            )
            print(f'{symbol} Current price updated! {bot["deal"]["current_price"]}')
            if bot and "deal" in bot:
                # Stop loss
                if "stop_loss" in bot["deal"] and float(bot["deal"]["stop_loss"]) > float(close_price):
                    deal = DealUpdates(bot)
                    res = deal.update_stop_limit(close_price)
                    if res == "completed":
                        self.start_stream()

                # Take profit trailling
                if bot["trailling"] == "true":

                    # Update trailling profit reached the first time
                    if ("trailling_profit" not in bot["deal"]) or float(bot["deal"]["take_profit_price"]) <= 0:
                        current_take_profit_price = float(bot["deal"]["buy_price"]) * (
                            1 + (float(bot["take_profit"]) / 100)
                        )
                    else:
                        # Update trailling profit after first time
                        current_take_profit_price = float(bot["deal"]["trailling_profit"]) * (
                            1 + (float(bot["take_profit"]) / 100)
                        )

                    if float(close_price) >= current_take_profit_price:
                        new_take_profit = current_take_profit_price * (
                            1 + (float(bot["take_profit"]) / 100)
                        )
                        # Update deal take_profit
                        bot["deal"]["take_profit_price"] = new_take_profit
                        bot["deal"]["trailling_profit"] = new_take_profit
                        # Update trailling_stop_loss
                        bot["deal"]["trailling_stop_loss_price"] = float(
                            new_take_profit
                        ) - (
                            float(new_take_profit) * (float(bot["trailling_deviation"]) / 100)
                        )

                        updated_bot = self.app.db.bots.find_one_and_update(
                            {"pair": symbol}, {"$set": {"deal": bot["deal"]}}
                        )
                        if not updated_bot:
                            self.app.db.bots.find_one_and_update(
                                {"pair": symbol},
                                {
                                    "$push": {
                                        "errors": f"Error updating trailling order {updated_bot}"
                                    }
                                },
                            )
                            # restart scanner
                            self.start_stream()
                        else:
                            print(
                                f"{symbol} Trailling updated! {current_take_profit_price}"
                            )
                    # Sell after hitting trailling stop_loss
                    if "trailling_stop_loss_price" in bot["deal"]:
                        price = bot["deal"]["trailling_stop_loss_price"]
                        if float(close_price) <= float(price):
                            deal = DealUpdates(bot)
                            completion = deal.trailling_stop_loss(price)
                            if completion == "completed":
                                self.start_stream()

                # Open safety orders
                # When bot = None, when bot doesn't exist (unclosed websocket)
                if (
                    "safety_order_prices" in bot["deal"]
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
