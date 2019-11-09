# %%
# libraries
import requests
import sys
import json
import pandas as pd
import numpy as np
import time as tm
from .environment import API_URL
import hmac
import hashlib
from urllib.parse import urlparse, urlencode
import math

class Data:
    base_url = API_URL.BINANCEAPI_BASE
    candlestick_url = API_URL.BINANCEAPI_CANDLESTICK

    def __init__(self, symbol, interval):
        self.interval = interval
        # if (asset != None) and (assetMarket != None):
        #     self.asset = asset
        #     self.assetMarket = assetMarket
        #     self.symbol = asset + assetMarket
        # else:
        self.symbol = symbol

    def request_data(self):
        # Get data for a single crypto e.g. BTT in BNB market
        params = {
            'symbol': self.symbol,
            'interval': self.interval,
        }
        r = requests.get(self.base_url + self.candlestick_url, params=params)
        data = r.json()
        return data

    def formatData(self, data):
        columns = ['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 'Quote asset volume',
                   'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'ignore']
        df = pd.DataFrame(data, columns=columns)
        # change default precision of decimals
        pd.set_option("display.precision", 8)
        # clean and parse data
        # dateFormat = '%d/%m/%Y'
        # df.drop('ignore', axis=1, inplace=True)
        df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
        df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
        df[['Open', 'High', 'Low', 'Close', 'Taker buy quote asset volume']] = df[['Open', 'High',
                                                                                   'Low', 'Close', 'Taker buy quote asset volume']].apply(lambda x: x.astype(float))
        df[['Volume', 'Taker buy base asset volume']] = df[[
            'Volume', 'Taker buy base asset volume']].apply(lambda x: x.astype(float))
        df.drop('ignore', axis=1, inplace=True)
        return df

    def api_data(self):
        return self.formatData(self.request_data())

    def static_data(self):
        with open("app/data/candlestick.json") as json_file:
            data = json.load(json_file)
            return self.formatData(data)


class Ticker24Data:

    base_url = API_URL.BINANCEAPI_BASE
    ticker24_url = API_URL.BINANCEAPI_TICKER24

    def __init__(self):
        """Request only ticker24 data
        """

    def request_data(self):
        r = requests.get(self.base_url + self.ticker24_url)
        data = r.json()
        return data

    def formatData(self, data):
        df = pd.DataFrame(data)
        return df

    def api_data(self):
        return self.formatData(self.request_data())


class Ticker_Price:

    base_url = API_URL.BINANCEAPI_BASE
    ticker_price = API_URL.BINANCEAPI_TICKER_PRICE

    def __init__(self):
        """Request only ticker24 data
        """

    def request_data(self, symbol=None):
        url = self.base_url + self.ticker_price
        params = {'symbol': symbol }
        r = requests.get(url=url, params=params)
        data = r.json()
        return data

    def formatData(self, data):
        df = pd.DataFrame(data)
        return df

    def api_data(self):
        return self.formatData(self.request_data())


class AVERAGE_PRICE:

    base_url = API_URL.BINANCEAPI_BASE
    average_price = API_URL.BINANCEAPI_AVERAGE_PRICE

    def __init__(self):
        """Request only ticker24 data
        """

    def request_data(self, symbol=None):
        url = self.base_url + self.average_price
        params = {'symbol': symbol }
        r = requests.get(url=url, params=params)
        data = r.json()
        return data

    def formatData(self, data):
        df = pd.DataFrame(data)
        return df

    def api_data(self):
        return self.formatData(self.request_data())

class Account:
    base_url = API_URL.BINANCEAPI_BASE
    account_url = API_URL.BINANCEAPI_ACCOUNT
    secret = API_URL.BINANCE_SECRET
    key = API_URL.BINANCE_KEY
    timestamp = int(round(tm.time() * 1000))

    def __init__(self, recvWindow=None):
        self.recvWindow = recvWindow

    def request_data(self):
        timestamp = int(round(tm.time() * 1000))
        # Get data for a single crypto e.g. BTT in BNB market
        params = {'recvWindow': 10000, 'timestamp': timestamp }
        headers = { 'X-MBX-APIKEY': self.key }
        url = self.base_url + self.account_url

        # Prepare request for signing
        r =  requests.Request('GET', url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(self.secret.encode('utf-8'), total_params.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature

        # Response after request
        res = requests.get(url=url, params=params, headers=headers)
        self.handle_error(res)
        data = res.json()
        return data

    def api_data(self):
        return self.request_data()
        # return self.formatData(self.request_data())

    # def static_data(self):
    #     with open("app/data/candlestick.json") as json_file:
    #         data = json.load(json_file)
    #         return self.formatData(data)

    def handle_error(self, req):
        try:
            req.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
            print('handle_error: Timeout')
        except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
            print('handle_error: Too many Redirects')
        except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
            print('handle_error', e)
            sleep(600.0)
            sys.exit(1)
        

class Exchange_Info:
    base_url = API_URL.BINANCEAPI_BASE
    info_url = API_URL.BINANCEAPI_EXCHANGE_INFO


    def __init__(self):
        """Request only ticker24 data
        """

    def lot_size(self):
        url = self.base_url + self.info_url
        r = requests.get(url=url)
        data = r.json()
        print(data)
        pass

    def request_data(self):
        # self.lot_size()
        url = self.base_url + self.info_url
        r = requests.get(url=url)
        data = r.json()
        return data

    def get_exchange_filters(self):
        exchangeFilters = self.request_data()['exchangeFilters']
        df = pd.DataFrame(exchangeFilters)
        return df

    def get_rate_limits(self):
        rateLimits = self.request_data().rateLimits
        df = pd.DataFrame(rateLimits)
        return df
    
    def server_time(self):
        serverTime = self.request_data().serverTime
        df = pd.DataFrame(serverTime)
        return df

    def server_timezone(self):
        timezone = self.request_data().timezone
        df = pd.DataFrame(timezone)
        return df

    def get_symbols(self):
        symbols = self.request_data()['symbols']
        df = pd.DataFrame(symbols)
        return df
    
    def find_quoteAsset(self, symbol):
        symbols = pd.DataFrame(self.get_symbols())
        quoteAsset = symbols.loc[symbols['symbol'] == symbol, 'quoteAsset']
        if symbol == 'BTCBTC':
            return 'BTC'
        else:
            return quoteAsset.values[-1]
    
    def find_baseAsset(self, symbol):
        symbols = pd.DataFrame(self.get_symbols())
        baseAsset = symbols.loc[symbols['symbol'] == symbol, 'baseAsset']
        return baseAsset.values[-1]

    def handle_error(self, req):
        try:
            req.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
            print('handle_error: Timeout')
        except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
            print('handle_error: Too many Redirects')
        except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
            print('handle_error', e)
            sys.exit(1)

