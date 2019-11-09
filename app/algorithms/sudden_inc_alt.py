import pandas as pd
import numpy as np
from utilities import Data, api
from utilities.indicators import kst_oscillator, keltner_channel, moving_average
from utilities.api import EnumDefinitions
from mailer import algo_notify

class Sudden_Inc_Alt:
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

    def __init__(self, symbol):
        self.symbol = symbol
        # index 3 = 15minutes chart intervals
        self.interval_idx = 2
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
        new_df.drop(['Volume', 'Quote asset volume', 'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume'], axis=1, inplace=True)
        return new_df


    def render_kst(self):
        df = self.obtain_data(self.interval_idx)
        k = kst_oscillator(df, 10, 25, 20, 30, 10, 10, 10, 15)
        ma_9 = moving_average(df, 9)
        new_df = k.merge(ma_9, how='outer')
        new_df.dropna(inplace=True)
        new_df.drop(['Volume', 'Quote asset volume', 'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume'], axis=1, inplace=True)
        new_df.reset_index(drop=True, inplace=True)
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
            return diff_close_open.all()
        else:
            # print('Low Trades, restarting execution {}'.format(self.interval))
            self.interval_idx += 1
            self.trend_signal()
            return


    def oscillator_signal(self):
        if self.interval_idx > 15:
            return False
        """MACD for oscillator signal
        Green candle higher than Upper bollinger
        Last 4 values are true
        """
        new_df = self.render_kst()
        if new_df.empty:
            return False
        last4_df = new_df.tail(4)
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        # If MACD diff line is higher than Signal line in the last 4 instances = buy
        diff_macd_signal = last4_df["KST_10_25_20_30_10_10_10_15"] > last4_df["MA_9"]
        # If no trades (close = open)
        diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        if diff_low_trades.empty:
            return diff_macd_signal.all()
        else:
            return self.oscillator_signal()
        # return diff_macd_signal.all()


    def oscillator_strength(self):
        new_df = self.render_kst()
        last4_df = new_df.tail(1)
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        # Difference between signal and macd diff
        diff_macd_signal = last4_df["KST_10_25_20_30_10_10_10_15"] - last4_df["MA_9"]
        # If diff_macd_signal positive = strong long/buying signal/increase
        # If diff_macd_signal negative = strong short/selling signal/decrease
        return diff_macd_signal.values[-1]

    def oscillator_value(self):
        new_df = self.render_kst()
        last4_df = new_df.tail(1)
        kst_value = last4_df["KST_10_25_20_30_10_10_10_15"]
        return kst_value.values[-1]

    def oscillator_slope(self):
        df = self.render_kst()
        df['diff'] = df['KST_10_25_20_30_10_10_10_15'].diff()
        df['change'] = df['diff'] / df['KST_10_25_20_30_10_10_10_15']
        df.drop(columns=['Open time', 'Open', 'High', 'Low', 'Close time', 'MA_9'], axis=1, inplace=True)
        return df['change'].tail(1).values[-1]