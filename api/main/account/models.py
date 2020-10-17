import time as tm
import hashlib
import hmac
import json
from urllib.parse import urlparse
import requests
import pandas as pd
from main.tools.handle_error import handle_error
from main.tools.jsonresp import jsonResp
import os

class Account:

    recvWindow = os.getenv("RECV_WINDOW")
    min_amount = 0.1  # MIN_NOTIONAL restriction by Binance
    secret = os.getenv('BINANCE_SECRET')
    key = os.getenv('BINANCE_KEY')
    base_url = os.getenv('BASE')
    account_url = os.getenv('ACCOUNT')
    candlestick_url = os.getenv('CANDLESTICK')
    exchangeinfo_url = os.getenv('EXCHANGE_INFO')

    def request_data(self):
        timestamp = int(round(tm.time() * 1000))
        # Get data for a single crypto e.g. BTT in BNB market
        params = {'recvWindow': self.recvWindow, 'timestamp': timestamp}
        headers = {'X-MBX-APIKEY': self.key}
        url = self.base_url + self.account_url

        # Prepare request for signing
        r = requests.Request('GET', url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(self.secret.encode(
            'utf-8'), total_params.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature

        # Response after request
        res = requests.get(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data

    def _exchange_info(self):
        url = self.base_url + self.exchangeinfo_url
        r = requests.get(url=url)
        return r.json()

    def get_balances(self):
        data = self.request_data()["balances"]
        df = pd.DataFrame(data)
        df['free'] = pd.to_numeric(df['free'])
        df['asset'] = df['asset'].astype(str)
        df.drop('locked', axis=1, inplace=True)
        df.reset_index(drop=True, inplace=True)
        # Get table with > 0
        balances = df[df['free'] > 0.000000].to_dict('records')

        # filter out empty
        # Return response
        resp = jsonResp(balances, 200)
        return resp

    def get_one_balance(self, symbol="BTC"):
        data = json.loads(self.get_balances().data)
        return next((x["free"] for x in data if x["asset"] == symbol), None)

    def find_quoteAsset(self, symbol):
        symbols = self._exchange_info()["symbols"]
        quote_asset = next((s for s in symbols if s["symbol"] == symbol), None)["quoteAsset"]
        return quote_asset

    def find_baseAsset(self, symbol):
        symbols = self._exchange_info()["symbols"]
        base_asset = next((s for s in symbols if s["symbol"] == symbol), None)["baseAsset"]
        return base_asset

    def get_symbols(self):
        symbols = self._exchange_info()["symbols"]
        return jsonResp(symbols, 200)
