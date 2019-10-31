import os
import sys
import time
from threading import Timer

import pandas as pd
import schedule
from datetime import datetime

from algorithms.safe_than_sorry_strategy import LONG_ALGO, SELL_FUNDS, CANDLESTICK_RENDERER
# from launchers.launch_sell import SELL_FUNDS
from orders.all_orders import ALL_ORDERS
from orders.new_order import BUY_ORDER, SELL_ORDER
from utilities.account import get_balances
from utilities.environment import API_URL
from utilities.get_data import Account, Exchange_Info, Ticker_Price
from utilities.log import logger

is_production = API_URL.BINBOARD_PROD_ENV
is_development = API_URL.BINBOARD_DEV_ENV
time_now = datetime.now()
midnight = time_now.replace(hour=0, minute=0, second=0, microsecond=0)
morning = time_now.replace(hour=6, minute=0, second=0, microsecond=0)

class ALGORITHM():
    """Encapsulation of the programmer function
    Creates a loop to insert funds as if real trading
    After long_algo is executed, it is added to the max_funds variable to simulate real trading
    
    Returns:
        [type] -- [description]
    """
    def __init__(self):
        self.max_funds = self.find_max_funds()
        pass

    # def sell_order(self, symbol, callback=None, arg=None):
    #     """Encapsulation new instance of SELL_ORDER
        
    #     Arguments:
    #         symbol {Enum String} -- Symbol to sell
        
    #     Keyword Arguments:
    #         callback {Func} -- Callback Function to call after sell order, 
    #           uses sleep to execute after successful call of main function (default: {None})
    #         arg {Any} -- Arguments to pass to callback function (default: {None})
    #     """
    #     order = SELL_ORDER(symbol)
    #     order.post_order()
    #     if callback:
    #         time.sleep(30.0)
    #         callback(arg)

    # def buy_order(self, symbol, callback=None, arg=None):
    #     """Encapsulation new instance of BUY_ORDER
        
    #     Arguments:
    #         symbol {Enum String} -- Symbol to buy
        
    #     Keyword Arguments:
    #         callback {Func} -- Callback Function to call after sell order, 
    #   uses sleep to execute after successful call of main function (default: {None})
    #         arg {Any} -- Arguments to pass to callback function (default: {None})
    #     """
    #     order = BUY_ORDER(symbol)
    #     order.post_order()
    #     if callback:
    #         time.sleep(30.0)
    #         callback(arg)

    def sell_funds(self):
        """Sell current funds according to Keltner channels
        If no sell signal, schedule to run again in 900 seconds
        Arguments:
            symbol {Enum string} -- Symbol matching funds (should be max amount)
        """
        sf = SELL_FUNDS(self.max_funds)
        print('running sell algo {}'.format(self.max_funds))
        if sf.launch_kc_sell():
            # sell_order(symbol)
            self.long_algo()
            

    def get_asset_current_price(self, symbol):
        tp = Ticker_Price()
        p = tp.request_data(symbol)['price']
        return p
    # If long asset return current asset do not buy
    # If current asset has higher strength do not buy

    def long_algo(self):
        la = LONG_ALGO()
        ei = Exchange_Info()
        long_asset = la.run_algo()
        # highest_balance_asset = self.find_max_funds()
        highest_balance_asset = self.max_funds
        # If there is an asset to long, and it does not coincide with currently held asset
        if long_asset:
            long_asset_quote = ei.find_quoteAsset(long_asset)
            highest_asset_quote = ei.find_quoteAsset(highest_balance_asset)
            if long_asset_quote == highest_asset_quote:
                """Asset held and asset to buy have same base asset
                Therefore, we can directly long
                """
                if highest_balance_asset == 'BTCBTC':
                    # buy_order(long_asset)

                    long_asset_price = self.get_asset_current_price(long_asset) # testing algo
                    print('Buy order {} @ {}'.format(long_asset, long_asset_price))
                    logger('Buy order {} @ {}'.format(long_asset, long_asset_price))
                else:
                    # sell_order(highest_balance_asset, buy_order, long_asset)
                    highest_balance_asset_price = self.get_asset_current_price(highest_balance_asset) # testing algo
                    long_asset_price = self.get_asset_current_price(long_asset) # testing algo
                    self.max_funds = long_asset
                    # Control point to avoid duplicate assets purchase
                    # Testing only
                    if highest_balance_asset == long_asset:
                        return False
                    print('Sell order {} @ {}'.format(highest_balance_asset, highest_balance_asset_price))
                    print('... and Buy order {} @ {}'.format(long_asset, long_asset_price))
                    logger('... and Buy order {} @ {}'.format(long_asset, long_asset_price))
            else:
                """Asset held and asset to buy have different base asset
                Therefore, we need to sell current asset before buying new one
                """
                if highest_asset_quote == 'BTC':
                    """Held asset is BTC market
                    Which means, asset to buy is BNB
                    """
                    symbol = long_asset_quote + highest_asset_quote
                    # buy_order(symbol)
                    symbol_price = self.get_asset_current_price(symbol) # testing algo
                    long_asset_price = self.get_asset_current_price(long_asset) # testing algo
                    text = 'Buy order {} @ {}. And buy order {} @ {}'.format(symbol, symbol_price, long_asset, long_asset_price)
                    print(text)
                    logger(text)
                    self.max_funds = long_asset
                else:
                    """Held asset is not BTC market
                    Which means, held asset is BNB (for now)
                    """
                    symbol = highest_asset_quote + long_asset_quote
                    # sell_order(symbol)

                    symbol_price = self.get_asset_current_price(symbol) # testing algo
                    print('Sell order {} @ {}'.format(symbol, symbol_price))
                    logger('Sell order {}'.format(symbol))
        return


    def find_max_funds(self):
        """Pick maximum number of funds
        1. Get all coins (assets) in funds to same base market (BTC)
            1a. Assume all cyptocurrencies in Binance are based on BTC
        2. If BTC exists in funds, add the at the end
        3. Contruct new Data Frame and get highest amount (total) of funds
        4. Use this highest amount to trade
        Returns:
            [DataFrame] -- Funds in DataFrame
        """
        balances = get_balances(0.001)
        btc_symbols = []
        tp = Ticker_Price()
        for index, asset in enumerate(balances['asset'].values):
            if asset != 'BTC':
                asset_props = tp.request_data(asset+'BTC')
                asset_props['amount'] = balances.iloc[index]['free']
                asset_props['total'] = float(asset_props['amount']) * float(asset_props['price'])
                btc_symbols.append(asset_props)

        if 'BTC' in balances['asset'].values:
            btc = {
                'symbol': 'BTCBTC',
                'amount': balances.loc[balances['asset'] == 'BTC', 'free'].values[-1],
                'price' : 1,
                'total': balances.loc[balances['asset'] == 'BTC', 'free'].values[-1],
            }
            btc_symbols.append(btc)
        btc_symbols = pd.DataFrame(btc_symbols)
        biggest_asset = btc_symbols.loc[btc_symbols['total'].idxmax(), 'symbol']
        return biggest_asset

    def programmer(self):
        highest_fund = self.max_funds
        if highest_fund != 'BTCBTC':
            # pass
            print(self.max_funds)
            if (time_now > midnight) & (time_now < morning):
                schedule.every(60).minutes.do(self.sell_funds)
            else:
                schedule.every(15).minutes.do(self.sell_funds)
        if (time_now > midnight) & (time_now < morning):
            schedule.every(30).minutes.do(self.long_algo)
        else:
            schedule.every(10).minutes.do(self.long_algo)
        while True:
            schedule.run_pending()
            time.sleep(1)
