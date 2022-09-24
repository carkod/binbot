import math
import copy
import requests

from apis import BinbotApi
from utils import InvalidSymbol, handle_binance_errors, round_numbers, supress_notation
from datetime import datetime


class Autotrade(BinbotApi):
    def __init__(self, pair, settings, algorithm_name, db_collection_name="paper_trading") -> None:
        """
        Initialize automatic bot trading.
        This hits the same endpoints as the UI terminal.binbot dashboard,
        but it's triggered by signals

        Args:
        settings: autotrade/test_autotrade settings
        algorithm_name: usually the filename
        db_collection_name: Mongodb collection name ["paper_trading", "bots"]
        """
        self.pair = pair
        self.settings = settings
        self.decimals = self.price_precision(pair)
        current_date = datetime.now().strftime("%Y-%m-%dT%H:%M")
        self.default_bot = {
            "pair": pair,
            "status": "inactive",
            "name": f"{algorithm_name}_{current_date}",
            "mode": "autotrade",
            "balance_size_to_use": settings["balance_size_to_use"],
            "balance_to_use": settings["balance_to_use"],
            "base_order_size": "0",
            "candlestick_interval": settings["candlestick_interval"],
            "take_profit": settings["take_profit"],
            "trailling": settings["trailling"],
            "trailling_deviation": settings["trailling_deviation"],
            "trailling_profit": 0,  # Trailling activation (first take profit hit)
            "orders": [],
            "stop_loss": settings["stop_loss"],
            "safety_orders": [],
            "errors": [],
        }
        self.db_collection_name = db_collection_name

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
    
    def default_5_so(self, balances, price, db_collection_name="paper_trading"):
        """
        Default -5% safety orders with 5 safety orders.

        This will create 5 safety orders that will trigger a BUY in when the price drops 5%.
        Each safety order is set to increase the BUY quantity exponentially by 1.2,
        starting from 10 USDT, which roughly will use up 172 USDT worth of funds.
        
        Take for example, in the BTC/USDT market, give current price 20,000 USDT per BTC:

        SO_1: Buy 10 USDT (qty) when price drops to @19,000 USDT per BTC
        SO_2: 10^1.2 = 15.84 USDT (qty) when price drops to @18,050 (-5% drop)
        SO_3: 15.84^1.2 = 27.52 USDT, when price drops to @17,147 (-5% drop)
        ...

        1. Get total balance
        2. Separate total balance evenly (exponentially increase)
        3. Set buy price (-5% drop) and quantity (exponential 1.2 increase)
        """
        exp_increase = 1.2
        total_num_so = 5
        available_balance = next((b["free"] for b in balances["data"] if b["asset"] == self.default_bot['balance_to_use']), None)
        initial_so = 10 # USDT

        if not available_balance:
            print(f"Not enough {self.default_bot['balance_to_use']} for safety orders")
            return

        # safety_order_qtys = float(available_balance) / total_num_so

        for index in range(total_num_so):
            count = index + 1
            threshold = count * 0.05
            buy_price = round_numbers(price - (price * threshold))
            so_size = round_numbers(initial_so ** exp_increase)

            if self.db_collection_name != "paper_trading" and not self.min_amount_check(self.pair, so_size):
                break
            initial_so = copy.copy(so_size)

            self.default_bot["safety_orders"].append({
                "name": f"so_{count}",
                "status": 0,
                "buy_price": float(buy_price),
                "so_size": float(so_size),
                "so_asset": "USDT",
                "errors": [],
                "total_commission": 0,
            })
        print("Safety orders set up: ", self.default_bot["safety_orders"])
        return
    
    def volatility_based_so(self):
        """
        Similar algorithm as `default_5_so`
        Instead of using a flat -5% drop, make it dependant on volatility
        that is, lowest and highest point.

        Usually 5% is enough for most markets. We can use by check the charts
        that so_5 tends to hit the lowest point
        """
        pass

    
    def activate_autotrade(self, trailling_deviation=None):
        """
        Run autotrade
        2. Create bot with given parameters from research_controller
        3. Activate bot
        """
        print(f"{self.db_collection_name} Autotrade running with {self.pair}...")
        # Check balance, if no balance set autotrade = 0
        # Use dahsboard add quantity
        res = requests.get(url=self.bb_balance_url)
        balances = handle_binance_errors(res)
        qty = 0

        if self.db_collection_name != "paper_trading":
            # Get balance that match the pair
            # Check that we have minimum binance required qty to trade
            for b in balances["data"]:
                if self.pair.endswith(b["asset"]):
                    qty = supress_notation(b["free"], self.decimals)
                    if self.min_amount_check(self.pair, qty):
                        # balance_size_to_use = 0.0 means "Use all balance". float(0) = 0.0
                        if float(self.default_bot["balance_size_to_use"]) != 0.0:
                            if b["free"] < float(self.default_bot["balance_size_to_use"]):
                                # Display warning and continue with full balance
                                print(f"Error: balance ({qty}) is less than balance_size_to_use ({float(self.default_bot['balance_size_to_use'])}). Autotrade will use all balance")
                            else:
                                qty = float(self.default_bot["balance_size_to_use"])
                    
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
                    self.default_bot.base_order_size = supress_notation(
                        base_order_size, self.decimals
                    )
                    pass

        # Can't get balance qty, because balance = 0 if real bot is trading
        # Base order set to default 1 to avoid errors
        # and because there is no matching engine endpoint to get market qty
        # So deal base_order should update this to the correct amount
        self.default_bot["base_order_size"] = "15" # min USDT order = 15
        self.default_bot["balance_to_use"] = "USDT" # For now we are always using USDT, safest and most coins/tokens
        self.default_bot["stop_loss"] = 0 # Using safety orders instead of stop_loss
        self.default_bot["trailling_deviation"] = float(self.settings["trailling_deviation"])

        if trailling_deviation:
            self.default_bot["trailling_deviation"] = trailling_deviation

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

        # Now that we have base_order price activate safety orders
        res = requests.get(url=f"{self.bb_test_bot_url}/{botId}")
        test_bot = res.json()["data"]
        self.default_bot.update(test_bot)
        self.default_bot.pop("_id")
        base_order_price = test_bot["deal"]["buy_price"]
        self.default_5_so(balances, base_order_price, "paper_trading")

        edit_bot_res = requests.put(url=f"{self.bb_test_bot_url}/{botId}", json=self.default_bot)
        edit_bot = handle_binance_errors(edit_bot_res)

        if ("error" in edit_bot and edit_bot["error"] == 1):
            print(
                f"Test Autotrade: {edit_bot['message']}",
                f"Pair: {self.pair}.",
            )
            return

        print(f"Succesful {self.db_collection_name} autotrade, opened test bot with {self.pair}!")
        pass


    def _legacy_activate_autotrade(self):
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
                    # balance_size_to_use = 0.0 means "Use all balance". float(0) = 0.0
                    if float(self.default_bot["balance_size_to_use"]) != 0.0:
                        if b["free"] < float(self.default_bot["balance_size_to_use"]):
                            # Display warning and continue with full balance
                            print(f"Error: balance ({qty}) is less than balance_size_to_use ({float(self.default_bot['balance_size_to_use'])}). Autotrade will use all balance")
                        else:
                            qty = float(self.default_bot["balance_size_to_use"])
                
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


        self.default_bot["trailling_deviation"] = self.settings["trailling_deviation"]

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
            print(f"Error activating bot {self.pair} with id {botId}")
            # Delete inactivatable bot
            payload = {
                "id": botId,
            }
            delete_res = requests.delete(url=f"{self.bb_bot_url}", params=payload)
            data = handle_binance_errors(delete_res)
            print(data)
            return
        
        # Now that we have base_order price activate safety orders
        res = requests.get(url=f"{self.bb_test_bot_url}/{botId}")
        test_bot = res.json()["data"]
        base_order_price = test_bot["deal"]["buy_price"]
        self.default_5_so(balances, base_order_price, "bots")

        edit_bot_res = requests.put(url=self.bb_bot_url, json=self.default_bot)
        edit_bot = handle_binance_errors(edit_bot_res)

        if ("error" in edit_bot and edit_bot["error"] == 1):
            print(
                f"Test Autotrade: {edit_bot['message']}",
                f"Pair: {self.pair}.",
            )
            return


        print(f"Succesful autotrade, opened bot with {self.pair}!")
