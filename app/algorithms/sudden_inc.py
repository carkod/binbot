# %%
import sys
# sys.path.append('D:\\algobin-notebook')
# sys.path.append('C:\\Users\\Carlos-Lenovo\\algobin')

import pandas as pd
import numpy as np
from utilities.get_data import Data
from utilities.indicators import bollinger_bands, moving_average, macd
from utilities.api import EnumDefinitions
from mailer import algo_notify
# %%


class Sudden_Inc:
    """ Sudden increase standard
        - Bollinger bands
        - MACD
        - Buy algorithm
        - Checks small periods (5m, 15m, 30m)
        Indicators are used to detect buy signal
    """

    def __init__(self, symbol):
        self.symbol = symbol
        # index 3 = 15minutes chart intervals
        self.interval_idx = 2

    def obtain_data(self, interval_idx):
        self.interval = EnumDefinitions.chart_intervals[interval_idx]
        gd = Data(interval=self.interval, symbol=self.symbol)
        df = gd.api_data()
        return df

    def render_bb(self):
        df = self.obtain_data(self.interval_idx)
        bb = bollinger_bands(df, 20)
        new_df = df.merge(bb)
        new_df.dropna(inplace=True)
        new_df.drop(['Volume', 'Quote asset volume', 'Number of trades','Taker buy base asset volume', 'Taker buy quote asset volume'], axis=1, inplace=True)
        return new_df

    def render_macd(self):
        df = self.obtain_data(self.interval_idx)
        m = macd(df, 25, 12)
        new_df = pd.concat([df, m], sort=False)
        new_df.dropna(inplace=True)
        new_df.drop(['Volume', 'Quote asset volume', 'Number of trades','Taker buy base asset volume', 'Taker buy quote asset volume'], axis=1, inplace=True)
        new_df.tail()
        return new_df

    def trend_signal(self):
        # Bollinger bands for trend signal in this case
        # Green candle higher than Upper bollinger
        # Last 4 values are true
        new_df = self.render_bb()
        last4_df = new_df.tail(4)
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        # If close price is higher than upper BB 4 times - buy
        diff_close_open = last4_df['Close'] > last4_df['BollingerB_20']
        # notification_text = 'Bollinger bands indicates Strong upward trend for {self.interval} period in market {self.symbol}'
        # coordinates = last4_df.values[-1].tolist()
        # If few trades, do not continue executing
        diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        if diff_low_trades.empty:
            return diff_close_open.all()
        else:
            # print('Low Trades, restarting execution {}'.format(self.interval))
            self.interval_idx += 1
            self.trend_signal()
            return

    def oscillator_signal(self):
        # MACD for oscillator signal
        # Green candle higher than Upper bollinger  
        # Last 4 values are true
        new_df = self.render_macd()
        last4_df = new_df.tail(4)
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        # If MACD diff line is higher than Signal line in the last 4 instances = buy
        diff_macd_signal = last4_df["MACDdiff_25_12"] > last4_df["MACDsign_25_12"]
        # notification_text = 'MACD indicates Strong upward trend for {self.interval} period in market {self.symbol}'
        # algo_notify(notification_text)
        # coordinates = last4_df.values[-1].tolist()
        diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        if diff_low_trades.empty:
            return diff_macd_signal.all()
        else:
            return self.oscillator_signal()
        # return diff_macd_signal.all()

    def oscillator_strength(self):
        new_df = self.render_macd()
        last4_df = new_df.tail(1)
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        # # If few trades, do not continue executing
        # diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        # if diff_low_trades.empty:
        #     return
        # else:
        #     return False
        # Difference between signal and macd diff
        diff_macd_signal = last4_df["MACDdiff_25_12"] - last4_df["MACDsign_25_12"]
        
        return diff_macd_signal.values[-1]
