from apis import BinbotApi
import requests

class Autotrade(BinbotApi):

    def __init__(self, pair) -> None:
        self.pair = pair
        self.default_bot = {
            "pair": pair,
            "status": "active",
            "name": "Default Bot",
            "mode": "autotrade",
            "balance_usage_size": "0.0001",
            "balance_to_use": "GBP",
            "base_order_size": "0.0001",  # MIN by Binance = 0.0001 BTC
            "base_order_type": "limit",
            "candlestick_interval": "15m",
            "take_profit": "3",
            "trailling": "false",
            "trailling_deviation": "0.63",
            "trailling_profit": 0,  # Trailling activation (first take profit hit)
            "orders": [],
            "stop_loss": "0",
            "safety_orders": {},
            "errors": [],
        }

    def get_balance_to_use(self):
        """
        Check balance to decide balance_to_use
        """
        pass
    
    def run(self):
        """
        autotrade
        """
        print("Autotrade running...")
        # Check balance, if no balance set autotrade = 0
        # Use dahsboard add quantity
        res = requests.post(url=self.bb_symbols_raw, json=self.default_bot)
        self.default_bot["balance_usage_size"] = 0.0001
        res = requests.post(url=self.bb_create_bot_url, json=self.default_bot)

        # If status 200 and res error == 1, append to controller errors
        
        # else activate bot with given id
        activate_bot_url = self.bb_activate_bot_url
        res = requests.post(url=self.bb_create_bot_url, json=self.default_bot)
        # if status 200 and res error == 0, bot opened successfuly
        pass