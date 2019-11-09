from threading import Timer

import pandas as pd

from algorithms.sell_bb import Sell
from algorithms.sell_kc import Sell_Alt
from mailer import algo_notify
from utilities.account import get_balances
from utilities.get_data import Account, Exchange_Info, Ticker_Price
from utilities.log import logger

class SELL_ALGO:

    restart_time = 60.0
    purchase_list = []
    
    # trailing sell
    sell_percentage = 0.2

    def launch_sudden_dec(self, sym, int, indexer, total_num):
        # print('Running Bollinger bands Algo')
        indexer += 1
        algo = Sell(sym[indexer], int)
        price = algo.price()

        if (algo.trend_signal() and algo.oscillator_signal() and algo.oscillator_strength() < 0):
            # sell if decreased more than 10% (stop-limit)
            if algo.sell_percentage(0.1):
                text = "Sell signal: {symbol}".format(symbol=sym[indexer])
                print(text)
                logger(text)
                # algo_notify(text)
                self.launch_sudden_dec(sym, int, indexer, total_num)
            else:
                text = "Sell signal {symbol}, but price did not fall less than {percentage}".format(symbol=sym[indexer], percentage=self.sell_perc)
                self.launch_sudden_dec(sym, int, indexer, total_num)
        else:
            if indexer < total_num:
                # print('false, launch again', indexer)
                self.launch_sudden_dec(sym, int, indexer, total_num)
            else:
                indexer = 0
                # report(purchase_list)
                print('no more to launch')
                logger('no more to launch')
                return 
                # timer = Timer(restart_time, launchs_sudden_inc_alt(symbol,indexer))
                # timer.start()

    def launch_sudden_dec_alt(self, sym, int, indexer, total_num):
        # print('Running Keltner Channels algo')
        indexer += 1
        algo = Sell_Alt(sym[indexer])
        price = algo.price()

        if (algo.trend_signal() and algo.oscillator_signal() and algo.oscillator_strength() < 0):
            if algo.percentage(self.sell_percentage):
                text = "Sell signal: {symbol}".format(symbol=sym[indexer])
                self.purchase_list.append(sym[indexer])
                print(text)
                logger(text)
                # algo_notify(text)
                self.launch_sudden_dec_alt(sym, int, indexer, total_num)
            else:
                text = "Sell signal {symbol}, but price did not fall less than {percentage}".format(symbol=sym[indexer], percentage=self.sell_percentage)
                self.launch_sudden_dec_alt(sym, int, indexer, total_num)
        else:
            if indexer < total_num:
                # print('false, launch again', indexer)
                self.launch_sudden_dec_alt(sym, int, indexer, total_num)
            else:
                indexer = 0
                # report(purchase_list)
                print('no more to launch')
                logger('no more to launch')
                return 

    def run_algo(self):
        # Assets
        balance_sym = get_balances()['asset']
        # Assets + base markets
        ei = Exchange_Info()
        symbols = ei.get_symbols()
        sell_symbols = symbols.loc[symbols['baseAsset'].isin(balance_sym), 'symbol']
        sell_symbols.reset_index(drop=True, inplace=True)

        # recursive variables
        indexer = 0
        total_num = len(sell_symbols) - 1
        
        # self.launch_sudden_dec(sell_symbols, interval)
        self.launch_sudden_dec_alt(sell_symbols, indexer, total_num)

class SELL_FUNDS():

    def __init__(self, symbol):
        self.symbol = symbol
        # self.interval = '15m'
    
    # def launch_bb_sell(self):
    #     """Bollinger bands selling
    #     """
    #     print('Running Bollinger bands Algo')
    #     algo = Sell(self.symbol, self.interval)

    #     if (algo.trend_signal() and algo.oscillator_signal() and algo.oscillator_strength() < 0):
    #         text = "Sell signal: {}".format(self.symbol)
    #         print(text)
    #         # algo_notify(text)

    #     else:
    #         print('no more to launch')
    #         return 
    

    def launch_kc_sell(self):
        """Keltner channels sell
        """
        # print('Running Keltner Channels algo')
        algo = Sell_Alt(self.symbol)
        price = algo.price()

        if (algo.trend_signal() and algo.oscillator_signal() and algo.oscillator_strength() < 0):
            
            text = "Sell signal: {} @ {}".format(self.symbol, price)
            print(text)
            # logger(text)
            return True
            # algo_notify(text)

        else:
            text = "No sell signal {} @ {}".format(self.symbol, price)
            print(text)
            # logger(text)
            return False
