import math

import requests

from apis import BinbotApi
from utils import InvalidSymbol, handle_binance_errors, supress_notation
from datetime import datetime


class Autotrade(BinbotApi):
    def __init__(self, pair, settings, amplitude=0) -> None:
        self.pair = pair
        self.amplitude = amplitude
        self.settings = settings
        self.decimals = self.price_precision(pair)
        current_date = datetime.now().strftime("%Y-%m-%dT%H:%M")
        self.default_bot = {
            "pair": pair,
            "status": "inactive",
            "name": f"{pair}_{current_date}",
            "mode": "autotrade",
            "balance_usage_size": 100,
            "balance_to_use": settings["balance_to_use"],
            "base_order_size": 0,
            "base_order_type": "limit",
            "candlestick_interval": settings["candlestick_interval"],
            "take_profit": settings["take_profit"],
            "trailling": settings["trailling"],
            "trailling_deviation": settings["trailling_deviation"],
            "trailling_profit": 0,  # Trailling activation (first take profit hit)
            "orders": [],
            "stop_loss": settings["stop_loss"],
            "safety_orders": {},
            "errors": [],
        }

    def handle_error(self, msg):
        """
        Check balance to decide balance_to_use
        """
        try:
            self.settings["system_logs"].append(msg)
        except AttributeError:
            self.settings["system_logs"] = []
            self.settings["system_logs"].append(msg)

        res = requests.put(url=self.bb_controller_url, json=self.settings)
        result = handle_binance_errors(res)
        return result

    def add_to_blacklist(self, symbol, reason=None):
        data = {"symbol": symbol, "reason": reason}
        res = requests.post(url=self.bb_blacklist_url, json=data)
        result = handle_binance_errors(res)
        return result

    def run(self):
        """
        Run autotrade
        2. Create bot with given parameters from research_controller
        3. Activate bot
        """
        print("Autotrade running...")
        # Check balance, if no balance set autotrade = 0
        # Use dahsboard add quantity
        res = requests.get(url=self.bb_balance_url)
        balances = handle_binance_errors(res)
        qty = 0

        # Get balance that match the pair
        # Check that we have minimum binance required qty to trade
        for b in balances["data"]:
            if self.pair.endswith(b["asset"]):
                qty = supress_notation(b["free"], self.decimals)
                if self.min_amount_check(self.pair, qty):
                    self.default_bot["base_order_size"] = qty
                    break
            # If we have GBP we can trade anything
            # And we have roughly the min BTC equivalent amount
            if (
                self.settings["balance_to_use"] == "GBP"
                and b["asset"] == "GBP"
                # Trading with less than 40 GBP will not be profitable
                and float(b["free"]) > 40
            ):
                base_asset = self.find_quoteAsset(self.pair)
                # e.g. XRPBTC
                if base_asset == "GBP":
                    self.default_bot["base_order_size"] = b["free"]
                    break
                try:
                    rate = self.ticker_price(f"{base_asset}GBP")
                except InvalidSymbol:
                    msg = f"Cannot trade {self.pair} with GBP. Adding to blacklist"
                    self.handle_error(msg)
                    self.add_to_blacklist(self.pair, msg)
                    print(msg)
                    return

                rate = rate["price"]
                qty = supress_notation(b["free"], self.decimals)
                # Round down to 6 numbers to avoid not enough funds
                base_order_size = (
                    math.floor((float(qty) / float(rate)) * 10000000) / 10000000
                )
                self.default_bot["base_order_size"] = supress_notation(
                    base_order_size, self.decimals
                )
                pass

        if float(self.default_bot["base_order_size"]) == 0:
            msg = f"No balance matched for {self.pair}"
            print(msg)
            return

        # Dynamic trailling
        # the bigger the candlestick swings the larger should the trailling be to avoid selling too soon
        self.default_bot["trailling_deviation"] = float(
            self.settings["trailling_deviation"]
        ) * (1 + float(self.amplitude))
        self.default_bot["stop_loss"] = float(
            self.settings["stop_loss"]
        ) * (1 + float(self.amplitude))

        # Create bot
        create_bot_res = requests.post(url=self.bb_bot_url, json=self.default_bot)
        create_bot = handle_binance_errors(create_bot_res)

        if "error" in create_bot and create_bot["error"] == 1:
            print(
                f"Autotrade: {create_bot['message']}",
                f"Pair: {self.pair}.",
                f"Balance: {b['free']}",
            )
            return

        # Activate bot
        botId = create_bot["botId"]
        print("Trying to activate bot...")
        res = requests.get(url=f"{self.bb_activate_bot_url}/{botId}")
        bot = handle_binance_errors(res)

        if "error" in bot and bot["error"] == 1:
            msg = f"Error activating bot {self.pair} with id {botId}"
            print(msg)
            # Delete inactivatable bot
            payload = {
                "id": botId,
            }
            delete_res = requests.delete(url=f"{self.bb_bot_url}", params=payload)
            data = handle_binance_errors(delete_res)
            print(data)
            return

        msg = f"Succesful autotrade, opened bot with {self.pair}!"
        print(msg)
