from apis import BinbotApi
import requests
from time import sleep
from utils import handle_binance_errors
class Autotrade(BinbotApi):

    def __init__(self, pair, settings) -> None:
        self.pair = pair
        self.settings = settings
        self.default_bot = {
            "pair": pair,
            "status": "inactive",
            "name": "Autotrade Bot",
            "mode": "autotrade",
            "balance_usage_size": None,
            "balance_to_use": "BNB",
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

    def handle_error(self, msg):
        """
        Check balance to decide balance_to_use
        """
        self.settings["errors"].append(msg)
        res = requests.put(url=self.bb_controller_url, json=self.settings)
    
    def run(self):
        """
        autotrade
        """
        print("Autotrade running...")
        # Check balance, if no balance set autotrade = 0
        # Use dahsboard add quantity
        res = requests.get(url=self.bb_balance_url)
        response = handle_binance_errors(res)

        for b in response["data"]:
            if b["asset"] in self.pair:
                self.default_bot["balance_usage_size"] = b["free"]
        

        if not self.default_bot["balance_usage_size"]:
            msg = f'No balance matched for {self.pair}'
            self.handle_error(msg)
            print(msg)
            return
        
        self.settings.pop("_id")
        self.default_bot.update(self.settings)
        create_bot_res = requests.post(url=self.bb_create_bot_url, json=self.default_bot)
        botId = handle_binance_errors(create_bot_res)
        if botId["error"] == 1:
            msg = f'Not enough funds to carry out autotrade with {self.pair}'
            self.handle_error(msg)
            return
        
        res = requests.get(url=f'{self.bb_activate_bot_url}/{botId}')
        response = handle_binance_errors(res)
        if response["error"] == 1:
            msg = f'Not enough funds to carry out autotrade with {self.pair}'
            self.handle_error(msg)
        else:
            msg = f'Succesful autotrade, opened bot with {self.pair}!'
            self.handle_error(msg)
        return