import math
import copy
import requests
import logging

from apis import BinbotApi
from utils import InvalidSymbol, handle_binance_errors, round_numbers, supress_notation
from datetime import datetime


class Autotrade(BinbotApi):
    def __init__(
        self, pair, settings, algorithm_name, db_collection_name="paper_trading"
    ) -> None:
        """
        Initialize automatic bot trading.
        This hits the same endpoints as the UI terminal.binbot dashboard,
        but it's triggered by signals

        There are two types of autotrade: autotrade and test_autotrade. The test_autotrade uses
        the paper_trading db collection and it doesn't use real quantities.

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
            "strategy": "long",
            "short_buy_price": 0,
            "short_sell_price": 0,
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

        res = requests.put(url=self.bb_autotrade_settings_url, json=self.settings)
        result = handle_binance_errors(res)
        return result

    def add_to_blacklist(self, symbol, reason=None):
        data = {"symbol": symbol, "reason": reason}
        res = requests.post(url=self.bb_blacklist_url, json=data)
        result = handle_binance_errors(res)
        return result

    def handle_price_drops(
        self,
        balances,
        price,
        per_deviation=1.2,
        exp_increase=1.2,
        total_num_so=3,
        trend="upward", # ["upward", "downward"] Upward trend is for candlestick_jumps and similar algorithms. Downward trend is for panic sells in the market
        lowest_price=0,
        sd=0
    ):
        """
        Sets the values for safety orders, short sell prices to hedge from drops in price.

        Safety orders here are designed to use qfl for price bounces: prices drop a bit but then overall the trend is bullish
        However short sell uses the short strategy: it sells the asset completely, to buy again after a dip.
        """
        available_balance = next(
            (
                b["free"]
                for b in balances["data"]
                if b["asset"] == self.default_bot["balance_to_use"]
            ),
            None,
        )
        initial_so = 10  # USDT

        if not available_balance:
            print(f"Not enough {self.default_bot['balance_to_use']} for safety orders")
            return

        if trend == "downtrend":
            down_short_buy_spread = total_num_so * (per_deviation / 100)
            down_short_sell_price = round_numbers(price - (price * 0.05))
            down_short_buy_price = round_numbers(down_short_sell_price - (down_short_sell_price * down_short_buy_spread))
            self.default_bot["short_sell_price"] = down_short_sell_price

            if lowest_price > 0 and lowest_price <= down_short_buy_price:
                self.default_bot["short_buy_price"] = lowest_price
            else:
                self.default_bot["short_buy_price"] = down_short_buy_price

            # most likely goes down, so no safety orders
            return

        for index in range(total_num_so):
            count = index + 1
            threshold = count * (per_deviation / 100)

            if index > 0:
                price = self.default_bot["safety_orders"][index - 1]["buy_price"]

            buy_price = round_numbers(price - (price * threshold))
            so_size = round_numbers(initial_so**exp_increase)
            initial_so = copy.copy(so_size)

            if count == total_num_so:
                # Increases price diff between short_sell_price and short_buy_price
                short_sell_spread = 0.05
                short_buy_spread = threshold
                short_sell_price = round_numbers(price - (price * threshold))
                short_buy_price = round_numbers(short_sell_price - (short_sell_price * threshold))

                if sd >= 0 and lowest_price > 0:
                    sd_buy_price = round_numbers(short_sell_price - (sd * 2))
                    if lowest_price < sd_buy_price or sd == 0:
                        short_buy_price = lowest_price
                    else:
                        short_buy_price = sd_buy_price

                self.default_bot["short_sell_price"] = short_sell_price
                self.default_bot["short_buy_price"] = short_buy_price
            else:
                self.default_bot["safety_orders"].append(
                    {
                        "name": f"so_{count}",
                        "status": 0,
                        "buy_price": float(buy_price),
                        "so_size": float(so_size),
                        "so_asset": "USDT",
                        "errors": [],
                        "total_commission": 0,
                    }
                )
        return

    def activate_autotrade(self, **kwargs):
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
        bot_url = self.bb_test_bot_url
        activate_url = self.bb_activate_test_bot_url

        if self.db_collection_name != "paper_trading":
            # Get balance that match the pair
            # Check that we have minimum binance required qty to trade
            for b in balances["data"]:
                if self.pair.endswith(b["asset"]):
                    qty = supress_notation(b["free"], self.decimals)
                    if self.min_amount_check(self.pair, qty):
                        # balance_size_to_use = 0.0 means "Use all balance". float(0) = 0.0
                        if float(self.default_bot["balance_size_to_use"]) != 0.0:
                            if b["free"] < float(
                                self.default_bot["balance_size_to_use"]
                            ):
                                # Display warning and continue with full balance
                                print(
                                    f"Error: balance ({qty}) is less than balance_size_to_use ({float(self.default_bot['balance_size_to_use'])}). Autotrade will use all balance"
                                )
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
                    try:
                        base_order_size = (
                            math.floor((float(qty) / float(rate)) * 10000000) / 10000000
                        )
                    except Exception as error:
                        print(error)
                    self.default_bot.base_order_size = supress_notation(
                        base_order_size, self.decimals
                    )
                    pass

            # Dynamic switch to real bot URLs
            bot_url = self.bb_bot_url
            activate_url = self.bb_activate_bot_url

        # Can't get balance qty, because balance = 0 if real bot is trading
        # Base order set to default 1 to avoid errors
        # and because there is no matching engine endpoint to get market qty
        # So deal base_order should update this to the correct amount
        if self.db_collection_name == "bots":
            self.default_bot["base_order_size"] = self.settings["base_order_size"]
        else:
            self.default_bot["base_order_size"] = "15"  # min USDT order = 15

        self.default_bot["balance_to_use"] = "USDT"  # For now we are always using USDT. Safest and most coins/tokens
        self.default_bot["stop_loss"] = 0  # Using safety orders instead of stop_loss
        # set default static trailling_deviation

        if "sd" in kwargs and "current_price" in kwargs:
            # dynamic take profit trailling_deviation, changes according to standard deviation
            spread = (kwargs["sd"] * 2) / kwargs["current_price"]
            self.default_bot["trailling_deviation"] = float(spread * 100)
        else:
            self.default_bot["trailling_deviation"] = float(
                self.settings["trailling_deviation"]
            )

        if "strategy" in kwargs:
            self.default_bot["strategy"] = kwargs["strategy"]

        # Create bot
        create_bot_res = requests.post(url=bot_url, json=self.default_bot)
        create_bot = handle_binance_errors(create_bot_res)

        if "error" in create_bot and create_bot["error"] == 1:
            print(
                f"Test Autotrade: {create_bot['message']}",
                f"Pair: {self.pair}.",
            )
            return

        # Activate bot
        botId = create_bot["botId"]
        print(f"Trying to activate {self.db_collection_name}...")
        res = requests.get(url=f"{activate_url}/{botId}")
        bot = handle_binance_errors(res)

        if "error" in bot and bot["error"] == 1:
            msg = f"Error activating bot {self.pair} with id {botId}"
            print(msg)
            print(bot)
            # Delete inactivatable bot
            payload = {
                "id": botId,
            }
            delete_res = requests.delete(url=bot_url, params=payload)
            data = handle_binance_errors(delete_res)
            print("Error trying to delete autotrade activation bot", data)
            return

        # Now that we have base_order price activate safety orders and dynamic trailling_profit
        res = requests.get(url=f"{bot_url}/{botId}")
        bot = res.json()["data"]
        self.default_bot.update(bot)
        self.default_bot.pop("_id")
        base_order_price = bot["deal"]["buy_price"]

        trend = "upward"
        lowest_price = 0
        sd = 0
        if "trend" in kwargs:
            trend = kwargs["trend"]

        if "lowest_price" in kwargs:
            lowest_price = kwargs["lowest_price"]
        
        if "sd" in kwargs:
            sd = kwargs["sd"]

        self.handle_price_drops(balances, base_order_price, trend=trend, lowest_price=lowest_price, sd=sd)

        # Set short_buy price, so that it's always bellow short_buy_price

        edit_bot_res = requests.put(url=f"{bot_url}/{botId}", json=self.default_bot)
        edit_bot = handle_binance_errors(edit_bot_res)

        if "error" in edit_bot and edit_bot["error"] == 1:
            print(f"Test Autotrade: {edit_bot['message']}",f"Pair: {self.pair}.")
            return

        print(
            f"Succesful {self.db_collection_name} autotrade, opened with {self.pair}!"
        )
        pass


def process_autotrade_restrictions(self, symbol, ws, algorithm, test_only=False, *args, **kwargs):
    """
    Refactored autotrade conditions.
    Previously part of process_kline_stream
    1. Checks if we have balance to trade
    2. Check if we need to update websockets
    3. Check if autotrade is enabled
    4. Check if test autotrades
    """
    logging.info("Running qfl_signals autotrade...")

    # If dashboard has changed any self.settings
    # Need to reload websocket
    if "update_required" in self.settings and self.settings["update_required"]:
        print("Update required, restart stream")
        self.terminate_websockets()
        self.start_stream(previous_ws=ws)
        pass
    
    # Wrap in try and except to avoid bugs stopping real bot trades
    try:
        if (
            symbol not in self.active_test_bots
            and int(self.test_autotrade_settings["autotrade"]) == 1
        ):
            if self.reached_max_active_autobots("paper_trading"):
                print("Reached maximum number of active bots set in controller settings")
            else:
                # Test autotrade runs independently of autotrade = 1
                test_autotrade = Autotrade(
                    symbol, self.test_autotrade_settings, algorithm, "paper_trading"
                )
                test_autotrade.activate_autotrade(**kwargs)
    except Exception as error:
        print(error)
        pass

    # Check balance to avoid failed autotrades
    check_balance_res = requests.get(url=self.bb_balance_estimate_url)
    balances = handle_binance_errors(check_balance_res)
    if "error" in balances and balances["error"] == 1:
        print(balances["message"])
        return

    balance_check = float(next((item["free"] for item in balances["data"]["balances"] if item["asset"] == self.settings["balance_to_use"]), 0))

    if balance_check < float(self.settings['base_order_size']):
        print("Not enough funds to autotrade.")
        return

    if (
        int(self.settings["autotrade"]) == 1
        and not test_only
    ):
        if self.reached_max_active_autobots("bots"):
            print("Reached maximum number of active bots set in controller settings")
        else:

            autotrade = Autotrade(symbol, self.settings, algorithm, "bots")
            autotrade.activate_autotrade(**kwargs)

    
    return
