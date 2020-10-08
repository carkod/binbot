from main import tools
import time as tm
import hashlib
import hmac
from urllib.parse import urlparse
import requests
import pandas as pd
from main.tools import handle_error
import os


class Account():

    recvWindow = 10000
    min_amount = 0.1  # MIN_NOTIONAL restriction by Binance

    def __init__(self):
        self.base_url = os.environ['BASE']
        self.account_url = os.environ['ACCOUNT']
        self.candlestick_url = os.environ['CANDLESTICK']
        self.secret = os.environ['BINANCE_SECRET']
        self.key = os.environ['BINANCE_KEY']        

    def request_data(self):
        timestamp = int(round(tm.time() * 1000))
        # Get data for a single crypto e.g. BTT in BNB market
        params = {'recvWindow': 10000, 'timestamp': timestamp}
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

    def get_balances(self):
        data = self.request_data()["balances"]
        df = pd.DataFrame(data)
        df['free'] = pd.to_numeric(df['free'])
        df['asset'] = df['asset'].astype(str)
        df.drop('locked', axis=1, inplace=True)
        df.reset_index(drop=True, inplace=True)
        # Get table with > 0
        balances = df[df['free'] > 0.000000]
        jsonResponse = balances.to_dict('records')

        # filter out empty
        # Return response
        resp = tools.JsonResp({"data": jsonResponse}, 200)
        return resp
