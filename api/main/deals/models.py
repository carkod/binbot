from flask import current_app as app
from flask import Flask, request
from passlib.hash import pbkdf2_sha256
from jose import jwt
from main import tools
from main import auth
import json
import time as tm
import hashlib
import hmac
import math
import sys
import time as tm
from urllib.parse import urlparse
import requests
import pandas as pd


class Deal:

    def __init__(self):
        self.timestamp = int(round(tm.time() * 1000))
        self.base_url = app.config['BASE']
        self.account_url = app.config['ACCOUNT']
        self.candlestick_url = app.config['CANDLESTICK']
        self.secret = app.config['BINANCE_SECRET']
        self.key = app.config['BINANCE_KEY']
        self.min_amount = 0.1  # MIN_NOTIONAL restriction by Binance
        self.recvWindow = 10000


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
        self.handle_error(res)
        data = res.json()
        return data

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
