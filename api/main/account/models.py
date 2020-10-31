import hashlib
import hmac
import json
import os
import time as tm
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import requests
from flask import current_app as app, request
from main.tools.handle_error import handle_error
from main.tools.jsonresp import jsonResp, jsonResp_message


class Account:

    recvWindow = os.getenv("RECV_WINDOW")
    secret = os.getenv('BINANCE_SECRET')
    key = os.getenv('BINANCE_KEY')
    account_url = os.getenv('ACCOUNT')
    exchangeinfo_url = os.getenv('EXCHANGE_INFO')
    ticker_price = os.getenv('TICKER_PRICE')

    def request_data(self):
        timestamp = int(round(tm.time() * 1000))
        # Get data for a single crypto e.g. BTT in BNB market
        params = {'recvWindow': self.recvWindow, 'timestamp': timestamp}
        headers = {'X-MBX-APIKEY': self.key}
        url = self.account_url

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
        url = self.exchangeinfo_url
        r = requests.get(url=url)
        return r.json()

    def _ticker_price(self):
        url = self.ticker_price
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

    def get_symbol_info(self):
        symbols = self._exchange_info()["symbols"]
        pair = request.view_args["pair"]
        symbol = next((s for s in symbols if s["symbol"] == pair), None)
        if symbol:
            return jsonResp({"data": symbol}, 200)
        else:
            return jsonResp_message("Pair not found", 200)

    def get_symbols(self):
        symbols = self._ticker_price()
        symbols_list = [x["symbol"] for x in symbols]
        symbols_list.sort()
        return jsonResp({"data": symbols_list}, 200)


class Balances(Account):

    def store_balance(self):
        """
        Cronjob that stores balances with its approximate current value in BTC
        """
        balances = self.get_balances().json
        ticker_price = self._ticker_price()
        total_btc = 0
        for b in balances:
            symbol = f"{b['asset']}BTC"
            price = next((x for x in ticker_price if x["symbol"] == symbol), None)
            if price:
                total_btc += b["free"]

        update_balances = {
            "balances": balances,
            "total_btc_value": total_btc
        }
        db = app.db.balances.save(update_balances, {"$currentDate": {"createdAt": "true"}})
        if request:
            resp = jsonResp({"message": "Balances updated!", "_id": db}, 200)
            return resp
        else:
            pass

    def get_value(self):
        resp = jsonResp({"message": "No balance found"}, 200)
        balance = list(app.db.balances.find({}))
        if balance:
            resp = jsonResp({"data": balance}, 200)
        return resp
