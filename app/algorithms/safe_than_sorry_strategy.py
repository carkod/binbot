
from threading import Timer

import numpy as np
import pandas as pd

from utilities import Data, api
from utilities.account import get_balances
from utilities.api import EnumDefinitions
from utilities.filters import Buy_Filters
from utilities.get_data import Account, Exchange_Info, Ticker_Price
from utilities.indicators import (keltner_channel, kst_oscillator, macd,
                                  moving_average)
from utilities.log import logger


class CANDLESTICK_RENDERER:
    """ Sudden increase alternative
        - KC (Ketlner Channels) for trend detection
        - KST (Know Sure Thing) for oscillator
        - Buy algorithm
        - Checks small periods (5m, 15m, 30m)
        Indicators are used to detect buy signal
        Keltner channels have less volatility than BB
        KST is smoother than MACD
        Combine KC with MACD and BB with KST for best results?
    """

    def __init__(self, symbol, interval_idx=2, oscillator_signal_threshold=6):
        self.symbol = symbol
        # index 3 = 15minutes chart intervals
        self.interval_idx = interval_idx
        # EnumDefinitions index. 6 = 2h chart interval. For short-term trading use smaller, long-term higher
        self.oscillator_signal_threshold = oscillator_signal_threshold
        self.price = None

    def obtain_data(self, interval_idx):
        self.interval = EnumDefinitions.chart_intervals[interval_idx]
        gd = Data(interval=self.interval, symbol=self.symbol)
        df = gd.api_data()
        return df

    def render_kc(self):
        df = self.obtain_data(self.interval_idx)
        kc = keltner_channel(df, 20)
        new_df = pd.concat([df, kc], sort=False)
        new_df.dropna(inplace=True)
        new_df.drop(['Volume', 'Quote asset volume', 'Number of trades',
                     'Taker buy base asset volume', 'Taker buy quote asset volume'], axis=1, inplace=True)
        return new_df

    def render_kst(self):
        df = self.obtain_data(self.interval_idx)
        k = kst_oscillator(df, 10, 15, 20, 30, 10, 10, 10, 15, 9)
        new_df = pd.concat([df, k], sort=False)
        new_df.dropna(inplace=True)
        new_df.drop(['Volume', 'Quote asset volume', 'Number of trades',
                     'Taker buy base asset volume', 'Taker buy quote asset volume'], axis=1, inplace=True)
        new_df.reset_index(drop=True, inplace=True)
        return new_df

    def render_macd(self):
        df = self.obtain_data(self.interval_idx)
        m = macd(df, 25, 12)
        new_df = pd.concat([df, m], sort=False)
        new_df.dropna(inplace=True)
        new_df.drop(['Volume', 'Quote asset volume', 'Number of trades',
                     'Taker buy base asset volume', 'Taker buy quote asset volume'], axis=1, inplace=True)
        new_df.tail()
        return new_df

    def trend_signal(self):
        if self.interval_idx > 15:
            return False
        """
        Bollinger bands for trend signal in this case
        Green candle higher than Upper bollinger
        Last 4 values are true
        """
        new_df = self.render_kc()
        if new_df.empty:
            return False

        last4_df = new_df.tail(4)

        # get price for printing
        self.price = last4_df['Close'].values[-1]

        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)

        # If close price is higher than upper BB 4 times - buy
        diff_close_open = last4_df['Close'] > last4_df['KelChU_20']
        # If no trades (close = open)
        diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        if diff_low_trades.empty:
            return False
        else:
            return diff_close_open.all()

    def trend_sell_signal(self):
        if self.interval_idx > 15:
            return False
        """
        Bollinger bands for trend signal in this case
        Green candle higher than Upper bollinger
        Last 4 values are true
        """
        new_df = self.render_kc()
        if new_df.empty:
            return False

        last4_df = new_df.tail(4)

        # get price for printing
        self.price = last4_df['Close'].values[-1]
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        # If close price is higher than upper BB 4 times - buy
        # diff_close_open = last4_df['Close'] < last4_df['KelChU_20']
        diff_close_open = last4_df['Close'] < last4_df['KelChM_20']
        # If no trades (close = open)
        diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        if diff_low_trades.empty:
            return False
        else:
            return diff_close_open.all()

    def oscillator_signal(self):
        print('Sudden Inc Algo, interval: {}'.format(self.interval_idx))
        new_df = self.render_kst()
        if new_df.empty:
            return False
        last4_df = new_df.tail(1)
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        self.price = last4_df['Close'].values[-1]
        # If MACD diff line is higher than Signal line in the last 4 instances = buy
        negative_oscillator = last4_df["KSTdiff_9"] < 0
        # If no trades (close = open)
        diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        if diff_low_trades.empty:
            return False
        if not negative_oscillator.all():
            return False

        if self.interval_idx < self.oscillator_signal_threshold:
            self.interval_idx += 1
            self.oscillator_signal()

        return True

    def oscillator_sell_signal(self):
        new_df = self.render_kst()
        if new_df.empty:
            return False
        last4_df = new_df.tail(1)
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        self.price = last4_df['Close'].values[-1]
        # If MACD diff line is lower than Signal line in the last 4 instances = buy
        diff_macd_signal = last4_df["KSTdiff_9"] < 0
        # If no trades (close = open)
        diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        if diff_low_trades.empty:
            return False
        if diff_macd_signal.values[-1] == False:
            return diff_macd_signal.all()

        if self.interval_idx < self.oscillator_signal_threshold:
            self.interval_idx += 1
            self.oscillator_sell_signal()
        return True

    def oscillator_strength(self):
        # new_df = self.render_kst()
        new_df = self.render_kst()
        last4_df = new_df.tail(1)
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        # Difference between signal and macd diff
        diff_macd_signal = last4_df["KST_10_15_20_30_10_10_10_15"] - \
            last4_df["KSTsign_9"]
        # If diff_macd_signal positive = strong long/buying signal/increase
        # If diff_macd_signal negative = strong short/selling signal/decrease
        return diff_macd_signal.values[-1]

    def oscillator_value(self):
        # new_df = self.render_kst()
        new_df = self.render_kst()
        # easier printing
        new_df.drop(columns=['Open time', 'Open', 'High',
                             'Low', 'Close time'], axis=1, inplace=True)
        last4_df = new_df.tail(1)
        kst_value = last4_df["KST_10_15_20_30_10_10_10_15"]
        return float(kst_value.values[-1])

    def oscillator_slope(self):
        # df = self.render_kst()
        df = self.render_kst()
        df['diff'] = df['KST_10_15_20_30_10_10_10_15'].diff()
        df['change'] = df['diff'] / df['KST_10_15_20_30_10_10_10_15']
        df.drop(columns=['Open time', 'Open', 'High', 'Low',
                         'Close time', 'KSTsign_9'], axis=1, inplace=True)
        return df['change'].tail(1).values[-1]

    def sell_percentage(self, pctg):
        """if price dropped more than percentage from highest peak

        Arguments:
            pctg {[string]} -- string
        """
        new_df = self.render_kst()
        new_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        peak = new_df['Close'].max()
        last = new_df.values[-1]
        percetage_chng = (last - peak)
        if percetage_chng > pctg:
            return True
        else:
            return False


class LONG_ALGO:

    # High volume?
    min_price = 0.00000000
    max_price = 20  # Change depending on value in Real currency
    ticker = Ticker_Price()
    data = ticker.api_data()
    ei = Exchange_Info()

    def __init__(self):
        self.purchase_list = []

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
                asset_props['total'] = float(
                    asset_props['amount']) * float(asset_props['price'])
                btc_symbols.append(asset_props)

        if 'BTC' in balances['asset'].values:
            btc = {
                'symbol': 'BTCBTC',
                'amount': balances.loc[balances['asset'] == 'BTC', 'free'].values[-1],
                'price': 1,
                'total': balances.loc[balances['asset'] == 'BTC', 'free'].values[-1],
            }
            btc_symbols.append(btc)
        btc_symbols = pd.DataFrame(btc_symbols)
        biggest_asset = btc_symbols.loc[btc_symbols['total'].idxmax(
        ), 'symbol']
        return biggest_asset

    def held_asset(self):
        find_max_funds = self.find_max_funds()
        algo = CANDLESTICK_RENDERER(find_max_funds)
        pair = {
            'symbol': find_max_funds,
            'strength': algo.oscillator_strength(),
            'oscillator': algo.oscillator_value()
        }
        return pair

    def launch_sudden_inc(self, symbol, indexer, total_num):
        indexer += 1
        if indexer < total_num:
            algo = CANDLESTICK_RENDERER(symbol[indexer])
            print('Scanning for assets to long. Index: {}, total: {}'.format(
                indexer, total_num))

            # Oscillator value screens overbought
            if (algo.oscillator_value() < 0 and algo.oscillator_signal() and symbol[indexer] != 'BNBETH'):
                self.price = algo.price
                text = "{symbol} has oscillator buy signal".format(
                    symbol=symbol[indexer])
                print(text)

                if algo.trend_signal():
                    pair = {
                        'symbol': symbol[indexer],
                        'strength': algo.oscillator_strength(),
                        'oscillator': algo.oscillator_value(),
                        'slope': algo.oscillator_slope()
                    }
                    text = "Buy signal: {symbol} @ {price}".format(
                        symbol=symbol[indexer], price=self.price)
                    print(text)
                    logger(text)
                    self.purchase_list.append(pair)

                else:
                    text = "{symbol} has no trend, rejected".format(
                        symbol=symbol[indexer])
                    print(text)

                self.launch_sudden_inc(symbol, indexer, total_num)
            else:
                text = "no buy signal, next"
                print(text)
                self.launch_sudden_inc(symbol, indexer, total_num)

        else:
            indexer = 0
            print('no more to launch, purchase list {}'.format(
                self.purchase_list))
            return

    def run_algo(self):
        """Runs algorithm with BB or KC
        Creates a list and returns the list

        Returns:
            [Symbol Enum String] -- Highest increase by oscillator strength
        """

        self.data['price'] = pd.to_numeric(self.data['price'])
        b = Buy_Filters(self.data)
        data = b.filter_symbol(self.data)
        # data = b.filter_prices(data, self.min_price, self.max_price)
        data = b.filter_by_btc(self.data)
        indexer = 0
        total_num = len(data['symbol']) - 1

        self.launch_sudden_inc(data['symbol'], indexer, total_num)

        # Format purchase_list into Data Frame
        df_purchaselist = pd.DataFrame(self.purchase_list)
        # if purchase list of cryptos is not empty
        if len(df_purchaselist):
            max_increase = df_purchaselist.loc[df_purchaselist['strength'].idxmax(
            ), 'symbol']
            # if purchase list max crypto is not stronger than currently held crypto
            held_asset_strength = self.held_asset()['strength']

            held_asset_oscillator = self.held_asset()['oscillator']
            held_asset_slope = self.held_asset()['oscillator']
            max_increase_strength = df_purchaselist.loc[df_purchaselist['strength'].idxmax(
            ), 'strength']
            max_increase_oscillator = df_purchaselist.loc[df_purchaselist['strength'].idxmax(
            ), 'oscillator']
            max_increase_slope = df_purchaselist.loc[df_purchaselist['slope'].idxmax(
            ), 'slope']

            # if held asset oscillator value is higher than found asset oscillator value, dont buy
            if held_asset_oscillator > max_increase_oscillator:
                max_increase = None

            # if held_asset_strength > max_increase_strength:
            #     max_increase = None

            # If oscillator strength is lower, it has higher potential to increase, therefore buy:
            # if held_asset_oscillator > max_increase_oscillator:
            #     max_increase = None

            # Overbought and oversold
            if (max_increase_oscillator > 10) or (max_increase_oscillator < -10):
                max_increase = None

            # if slope is positive and higher, it is time to buy
            # if (max_increase_slope < held_asset_slope):
            #     max_increase = None

        else:
            max_increase = None

        # if matches asset in funds, do not proceed - cannot control this
        # because testing fund_assets injection is not controlled here, it is controlled in forward_testing
        text = 'found maximum symbol {}'.format(max_increase)
        print(text)
        logger(text)
        return max_increase


class SHORT_ALGO:

    restart_time = 60.0
    purchase_list = []

    # trailing sell
    sell_percentage = 0.2

    def __init__(self, sell_symbol=None):
        self.sell_symbol = sell_symbol

    def launch_kc(self, sym, int, indexer, total_num):
        indexer += 1
        algo = CANDLESTICK_RENDERER(sym[indexer])

        if (algo.oscillator_sell_signal() and float(algo.oscillator_value()) > 0):
            text = "Sell signal: {symbol}".format(symbol=sym[indexer])
            self.purchase_list.append(sym[indexer])
            print(text)
            self.launch_kc(sym, int, indexer, total_num)
    
        else:
            if indexer < total_num:
                # print('false, launch again', indexer)
                self.launch_kc(sym, int, indexer, total_num)
            else:
                indexer = 0
                print('no more to launch')
                return

    def run_algo(self):
        # Assets
        balance_sym = get_balances()['asset']
        # Assets + base markets
        ei = Exchange_Info()
        symbols = ei.get_symbols()
        sell_symbols = symbols.loc[symbols['baseAsset'].isin(
            balance_sym), 'symbol']
        sell_symbols.reset_index(drop=True, inplace=True)

        # recursive variables
        indexer = 0
        total_num = len(sell_symbols) - 1

        # self.launch_sudden_dec(sell_symbols, interval)
        self.launch_kc(sell_symbols, int, indexer, total_num)


class SELL_FUNDS():

    def __init__(self, symbol):
        self.symbol = symbol

    def launch_kc_sell(self):
        """Keltner channels sell
        """
        # print('Running Keltner Channels algo')
        algo = CANDLESTICK_RENDERER(self.symbol)

        # Moderate approach to selling
        # Sell if oscillator tells so
        if algo.oscillator_sell_signal():
            text = "Sell signal (oscillator signal only): {symbol}".format(
                symbol=self.symbol)
            print(text)
            return True

        else:
            text = "No sell signal {symbol}".format(symbol=self.symbol)
            print(text)
            return False
