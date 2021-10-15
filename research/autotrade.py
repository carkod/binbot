from apis import BinbotApi
import requests
from time import sleep
from utils import handle_binance_errors, supress_notation
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
        1. Check balance
        2. Create bot with given parameters from research_controller
        3. Activate bot

        To do:
        - If no balance stop autotrade
        - Stop creating bots when there is no balance.
        - Stop creating bots with the same pair if there is already a bot active
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
                qty = supress_notation(b["free"], self.price_precision(self.pair))
                if self.min_amount_check(self.pair, qty):
                    self.default_bot["balance_usage_size"] = qty
                else:
                    return
        

        if not self.default_bot["balance_usage_size"]:
            msg = f'No balance matched for {self.pair}'
            self.handle_error(msg)
            print(msg)
            return

        self.settings.pop("_id")
        self.default_bot.update(self.settings)
        create_bot_res = requests.post(url=self.bb_create_bot_url, json=self.default_bot)
        botId = handle_binance_errors(create_bot_res)
        if "error" in botId and botId["error"] == 1:
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