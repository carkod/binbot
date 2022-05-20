import requests

from apis import BinbotApi
from utils import handle_binance_errors
from datetime import datetime


class TestAutotrade(BinbotApi):
    def __init__(self, pair, settings, algorithm, *args) -> None:
        self.pair = pair
        self.settings = settings
        self.decimals = self.price_precision(pair)
        current_date = datetime.now().strftime("%Y-%m-%dT%H:%M")
        self.args = args[0]
        self.default_bot = {
            "pair": pair,
            "status": "inactive",
            "name": f"{algorithm}_{current_date}",
            "mode": "test autotrade",
            "balance_size_to_use": settings["balance_size_to_use"],
            "balance_to_use": settings["balance_to_use"],
            "base_order_size": 0,
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
        print("Test Autotrade running...")
        # Check balance, if no balance set autotrade = 0
        # Use dahsboard add quantity
        res = requests.get(url=self.bb_balance_url)

        # Can't get balance qty, because balance = 0 if real bot is trading
        # Base order set to default 1 to avoid errors
        # and because there is no matching engine endpoint to get market qty
        # So deal base_order should update this to the correct amount
        self.default_bot["base_order_size"] = 1
        try:
            self.default_bot["trailling_deviation"] = self.args[0]
        except IndexError:
            self.default_bot["trailling_deviation"] = float(self.settings["trailling_deviation"])

        # Create bot
        create_bot_res = requests.post(url=self.bb_test_bot_url, json=self.default_bot)
        create_bot = handle_binance_errors(create_bot_res)

        if ("error" in create_bot and create_bot["error"] == 1):
            print(
                f"Test Autotrade: {create_bot['message']}",
                f"Pair: {self.pair}.",
            )
            return

        # Activate bot
        botId = create_bot["botId"]
        print("Trying to activate test bot...")
        res = requests.get(url=f"{self.bb_activate_test_bot_url}/{botId}")
        bot = handle_binance_errors(res)

        if "error" in bot and bot["error"] == 1:
            msg = f"Error activating bot {self.pair} with id {botId}"
            print(msg)
            # Delete inactivatable bot
            payload = {
                "id": botId,
            }
            delete_res = requests.delete(url=f"{self.bb_test_bot_url}", params=payload)
            data = handle_binance_errors(delete_res)
            print(data)
            return

        print(f"Succesful test autotrade, opened test bot with {self.pair}!")
        pass
