from threading import Timer

import pandas as pd

from algorithms.sudden_inc import Sudden_Inc
from algorithms.sudden_inc_alt import Sudden_Inc_Alt
from mailer import algo_notify
from utilities.api import EnumDefinitions
from utilities.filters import Buy_Filters
from utilities.get_data import Ticker_Price, Exchange_Info
from utilities.log import logger
from utilities.account import get_balances


class LONG_ALGO:

    # High volume?
    min_price = 0.00000000
    max_price = 20 # Change depending on value in Real currency
    ticker = Ticker_Price()
    data = ticker.api_data()
    ei = Exchange_Info()

    def __init__(self):
        self.purchase_list = []
        pass

    def report(self, list):
        """Send email with list of cryptos to buy
        
        Arguments:
            list {List} -- [Array cryptos for email body]
        """
        for coin in list:
            message = 'Buy signal for: {}'.format(coin)
    
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
    
    def held_asset(self):
        find_max_funds = self.find_max_funds()
        algo = Sudden_Inc_Alt(find_max_funds)
        pair = {
            'symbol': find_max_funds,
            'strength': algo.oscillator_strength(),
            'oscillator': algo.oscillator_value()
        }
        return pair


        
    def launch_sudden_inc(self, symbol, indexer, total_num):
        indexer += 1
        algo = Sudden_Inc(symbol[indexer])
        self.price = algo.price
        
        if ((algo.trend_signal() and algo.oscillator_signal())):
            text = "Buy signal: {symbol} @ {price}".format(symbol=symbol[indexer], price=self.price)
            pair = {
                'symbol': symbol[indexer],
                'strength': algo.oscillator_strength(),
            }
            # print(text)
            self.purchase_list.append(pair)
            logger(text)
            self.launch_sudden_inc(symbol, indexer, total_num)
            
        else:
            if indexer < total_num:
                # print('false, launch again', indexer)
                self.launch_sudden_inc(symbol, indexer, total_num)
            else:
                indexer = 0
                # self.report(self.purchase_list)
                print('no more to launch')
                logger('no more to launch')
                return 

    def launch_sudden_inc_alt(self, symbol, indexer, total_num):
        # print('Running Keltner Channels algo')
        indexer += 1
        algo = Sudden_Inc_Alt(symbol[indexer])
        self.price = algo.price
        
        if (algo.oscillator_signal() and symbol[indexer] != 'BNBETH'):
            text = "Buy signal: {symbol} @ {price}".format(symbol=symbol[indexer], price=self.price)
            print(text)
            if algo.trend_signal():
                pair = {
                    'symbol': symbol[indexer],
                    'strength': algo.oscillator_strength(),
                    'oscillator': algo.oscillator_value(),
                    'slope': algo.oscillator_slope()
                }
                text = "Buy signal: {symbol} @ {price}".format(symbol=symbol[indexer], price=self.price)
                logger(text)
                # print(text)
                self.purchase_list.append(pair)
                
                # algo_notify(text)
                self.launch_sudden_inc_alt(symbol, indexer, total_num)
                
            else:
                if indexer < total_num:
                    # print('false, launch again', indexer)
                    self.launch_sudden_inc_alt(symbol, indexer, total_num)
                else:
                    indexer = 0
                    # self.report(purchase_list)
                    print('no more to launch, purchase list {}'.format(self.purchase_list))
                    logger('no more to launch, purchase list {}'.format(self.purchase_list))
                    return False
        else:
            text = "Buy signal: {symbol} @ {price} has no trend, rejected".format(symbol=symbol[indexer], price=self.price)
            print(text)
            self.launch_sudden_inc_alt(symbol, indexer, total_num)

    """Runs algorithm with BB or KC
    Creates a list and returns the list
    
    Returns:
        [Symbol Enum String] -- Highest increase by oscillator strength
    """
    def run_algo(self):
        self.data['price'] = pd.to_numeric(self.data['price'])
        b = Buy_Filters(self.data)
        data = b.filter_symbol(self.data)
        # data = b.filter_prices(data, self.min_price, self.max_price)
        data = b.filter_by_btc(self.data)
        indexer = 0
        total_num = len(data['symbol']) - 1

        """ 
            Less restrictive uses KC, which buys signal and sell signal comes earlier
            Bands are narrower
            Osciallator is less volatile (KTC)
        """
        # less_restrictive_algo = launch_sudden_inc(symbol, indexer)
        # self.launch_sudden_inc(data['symbol'], indexer, total_num)

        """
            More restrictive uses BB, which buys signal and sell signal comes later
            Bands are wider
            Oscillator is more volatile (MACD)
            more_restrictive_algo = launch_sudden_inc_alt(symbol, indexer)
        """
        self.launch_sudden_inc_alt(data['symbol'], indexer, total_num)

        # Format purchase_list into Data Frame
        df_purchaselist = pd.DataFrame(self.purchase_list)
        # if purchase list of cryptos is not empty
        if len(df_purchaselist):
            max_increase = df_purchaselist.loc[df_purchaselist['strength'].idxmax(), 'symbol']
            # if purchase list max crypto is not stronger than currently held crypto
            held_asset_strength = self.held_asset()['strength']

            held_asset_oscillator = self.held_asset()['oscillator']
            held_asset_slope = self.held_asset()['oscillator']
            max_increase_strength = df_purchaselist.loc[df_purchaselist['strength'].idxmax(), 'strength']
            max_increase_oscillator = df_purchaselist.loc[df_purchaselist['strength'].idxmax(), 'oscillator']
            max_increase_slope = df_purchaselist.loc[df_purchaselist['slope'].idxmax(), 'slope']

            # if matches asset in funds, do not proceed
            asset = self.ei.find_baseAsset(max_increase)
            funds_asset = self.ei.find_baseAsset(self.held_asset()['symbol'])
            if asset == funds_asset:
                max_increase = None

            # if held asset oscillator value is higher than found asset oscillator value, dont buy
            # if held_asset_oscillator > max_increase_oscillator:
            #     max_increase = None

            
            if held_asset_strength > max_increase_strength:
                max_increase = None

            # If oscillator strength is lower, it has higher potential to increase, therefore buy:
            if held_asset_oscillator > max_increase_oscillator:
                max_increase = None
            
            # Overbought and oversold
            if (max_increase_oscillator > 20) or (max_increase_oscillator < -20):
                max_increase = None

            # if slope is positive and higher, it is time to buy
            if (max_increase_slope < 0) or (max_increase_slope < held_asset_slope):
                max_increase = None

        else:
            max_increase = None
        print('found maximum symbol {}'.format(max_increase))
        logger('found maximum symbol {}'.format(max_increase))
        return max_increase
