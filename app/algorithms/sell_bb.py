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


class Sell:
    """ Sudden increase standard
        - Bollinger bands
        - MACD
        - Buy algorithm
        - Checks small periods (5m, 15m, 30m)
        Indicators are used to detect buy signal
    """
        # df = gd.static_data()

    def __init__(self, symbol, interval):
        self.symbol = symbol
        self.interval = interval
        gd = Data(interval=interval, symbol=symbol)
        self.df = gd.api_data()


    def low_trades(self, last4_df):
        # If few trades, do not continue executing
        diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        if diff_low_trades.empty:
            pass
        else:
            return False
    
    def render_bb(self):
        
        bb = bollinger_bands(self.df, 20)
        new_df = self.df.merge(bb)
        new_df.dropna(inplace=True)
        new_df.drop(['Volume', 'Quote asset volume', 'Number of trades','Taker buy base asset volume', 'Taker buy quote asset volume'], axis=1, inplace=True)
        return new_df

    def render_macd(self):
        
        m = macd(self.df, 25, 12)
        new_df = pd.concat([self.df, m], sort=False)
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
        diff_close_open = last4_df['Close'] < last4_df["Bollinger%b_20"]
        # notification_text = 'Bollinger bands indicates Strong upward trend for {self.interval} period in market {self.symbol}'
        coordinates = last4_df.values[-1].tolist()
        # If few trades, do not continue executing
        diff_low_trades = last4_df.loc[last4_df["Close"] == last4_df["Open"]]
        if diff_low_trades.empty:
            return diff_close_open.all()
        else:
            return False
        # return diff_close_open.all()

    def oscillator_signal(self):
        # MACD for oscillator signal
        # Green candle higher than Upper bollinger
        # Last 4 values are true
        new_df = self.render_macd()
        last4_df = new_df.tail(2)
        last4_df.drop(['Low', 'High', 'Open time'], axis=1, inplace=True)
        # If MACD diff line is higher than Signal line in the last 4 instances = buy
        diff_macd_signal = last4_df["MACDdiff_25_12"] < last4_df["MACDsign_25_12"]
        # notification_text = 'MACD indicates Strong upward trend for {self.interval} period in market {self.symbol}'
        coordinates = last4_df.values[-1].tolist()
        return diff_macd_signal.all()

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
        # notification_text = 'MACD indicates Strong upward trend for {self.interval} period in market {self.symbol}'
        # algo_notify(notification_text)
        # If diff_macd_signal positive = strong long/buying signal/increase
        # If diff_macd_signal negative = strong short/selling signal/decrease
        return diff_macd_signal.values[-1]
