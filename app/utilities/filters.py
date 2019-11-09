import pandas as pd
import numpy as np
from utilities.get_data import Data
from utilities.indicators import bollinger_bands, moving_average, macd
from utilities.api import EnumDefinitions
from mailer import algo_notify
from utilities.get_data import Exchange_Info

class Buy_Filters:

    ei = Exchange_Info()

    def __init__(self, df):
        self.df = df

    def filter_prices(self, df, min_price, max_price):
        data = df.loc[df['price'] > min_price]
        data = df.loc[df['price'] < max_price]
        data.dropna(inplace=True)
        data.reset_index(drop=True,inplace=True)
        return data

    def filter_by_btc(self, df):
        """Filters by market AND by price (converted to approx 20 USD dollars per market)
        e.g. Only BTC < 20 dollars
        """
        max_btc_price = 0.00014
        # Numpy + Python Bug. Set engine to Python
        indices = df.query('(symbol.str.endswith("BTC") & price < 0.004) | (symbol.str.endswith("BNB") & price < 2)', engine="python").index
        data = df.ix[indices]
        data.reset_index(drop=True,inplace=True)
        return data

    def filter_market(self, df, base_market):
        data = df.loc[df['symbol'].str.endswith(base_market)]
        data.dropna(inplace=True)
        data.reset_index(drop=True,inplace=True)
        return data

    def filter_symbol(self, df):
        # these coins are non-purchasable, or market
        usd = ("USDT", "USDC", "TUSD", "USDS", "PAXBNB", "BNBETH", "ETH")
        data = df[~df['symbol'].str.endswith(usd)]
        return data

    def clean(self, data):
        data.dropna(inplace=True)
        data.reset_index(drop=True,inplace=True)
        return data