from time import sleep

import requests

from apis import BinbotApi, CoinBaseApi
from utils import handle_binance_errors, supress_notation
import math

class Autotrade(BinbotApi):
    def __init__(self, pair, settings) -> None:
        self.pair = pair
        self.settings = settings
        self.decimals = self.price_precision(pair)
        self.default_bot = {
            "pair": pair,
            "status": "inactive",
            "name": "Autotrade Bot",
            "mode": "autotrade",
            "balance_usage_size": None,
            "balance_to_use": "GBP",
            "base_order_size": "0.0001",  # MIN by Binance = 0.0001 BTC
            "base_order_type": "limit",
            "candlestick_interval": "1h",
            "take_profit": "3",
            "trailling": "false",
            "trailling_deviation": "0.63",
            "trailling_profit": 0,  # Trailling activation (first take profit hit)
            "orders": [],
            "stop_loss": "0",
            "safety_orders": {},
            "errors": [],
        }

    def handle_error(self, msg):
        """
        Check balance to decide balance_to_use
        """
        try:
            self.settings["errors"].append(msg)
        except AttributeError:
            self.settings["errors"] = []
            self.settings["errors"].append(msg)

        res = requests.put(url=self.bb_controller_url, json=self.settings)
        result = handle_binance_errors(res)
        return result

    def run(self):
        """
        Run autotrade
        1. Check balance, if no balance stop autotrade
        2. Create bot with given parameters from research_controller
        3. Activate bot
        """
        print("Autotrade running...")
        # Check balance, if no balance set autotrade = 0
        # Use dahsboard add quantity
        res = requests.get(url=self.bb_balance_url)
        response = handle_binance_errors(res)

        # Get balance that match the pair
        # Check that we have minimum binance required qty to trade
        for b in response["data"]:
            if b["asset"] in self.pair:
                qty = supress_notation(b["free"], self.decimals)
                if self.min_amount_check(self.pair, qty):
                    self.default_bot["balance_usage_size"] = qty
                else:
                    return
            # If we have GBP we can trade anything
            # And we have roughly the min BTC equivalent amount
            if (
                self.settings["balance_to_use"] == "GBP"
                and b["asset"] == "GBP"
                and float(b["free"]) > 40
            ):
                coinbase_api = CoinBaseApi()
                base_asset = self.find_quoteAsset(self.pair)
                rate = coinbase_api.get_conversion(base_asset, "GBP")
                qty = supress_notation(b["free"], self.decimals)
                # Round down to 6 numbers to avoid not enough funds
                balance_usage_size = (math.floor((float(qty) / float(rate)) * 1000000) / 1000000) * 1.0002
                self.default_bot["balance_usage_size"] = supress_notation(float(qty) / float(rate), self.decimals)
                break

        if not self.default_bot["balance_usage_size"]:
            msg = f"No balance matched for {self.pair}"
            self.handle_error(msg)
            print(msg)
            return

        self.settings.pop("_id")
        self.default_bot.update(self.settings)
        create_bot_res = requests.post(url=self.bb_bot_url, json=self.default_bot)
        botId = handle_binance_errors(create_bot_res)["botId"]
        if "error" in botId and botId["error"] == 1:
            msg = f"Not enough funds to carry out autotrade with {self.pair}"
            self.handle_error(msg)
            return

        res = requests.get(url=f"{self.bb_activate_bot_url}/{botId}")
        response = handle_binance_errors(res)
        if response["error"] == 1:
            msg = f"Not enough funds to carry out autotrade with {self.pair}"
            self.handle_error(msg)
        else:
            msg = f"Succesful autotrade, opened bot with {self.pair}!"
            self.handle_error(msg)
        return
