import hashlib
import hmac
import json
import os
import time as tm
from urllib.parse import urlparse

import pandas as pd
import requests
from flask import current_app as app, request
from main.tools.handle_error import handle_error
from main.tools.jsonresp import jsonResp, jsonResp_message
from datetime import datetime, timedelta

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


class Assets(Account):

    def store_balance(self):
        """
        Cronjob that stores balances with its approximate current value in BTC
        """
        balances = self.get_balances().json
        ticker_price = self._ticker_price()
        total_btc = 0
        for b in balances:

            # Ordinary coins found in balance
            symbol = f"{b['asset']}BTC"
            price = next((x for x in ticker_price if x["symbol"] == symbol), None)
            if price:
                btc = b["free"] * float(price["price"])
                b["btc_value"] = btc

            # USD tether coins found in balance
            if b["asset"].find("USD") > -1:
                symbol = f"BTC{b['asset']}"
                price = next((x for x in ticker_price if x["symbol"] == symbol), None)
                btc = b["free"] / float(price["price"])
                b["btc_value"] = btc

            # BTC found in balance
            if b["asset"] == "BTC":
                btc = b["free"]
                b["btc_value"] = btc

            total_btc += btc

        update_balances = {
            "balances": balances,
            "total_btc_value": total_btc,
            "updatedTime": datetime.now().timestamp()
        }
        db = app.db.assets.insert_one(update_balances)
        if request and db:
            resp = jsonResp({"message": "Balances updated!"}, 200)
            return resp
        if not db:
            resp = jsonResp({"message": "Failed to update Balance", "error": db}, 200)
            return resp
        else:
            pass

    def get_value(self):
        resp = jsonResp({"message": "No balance found"}, 200)
        interval = request.view_args["interval"]
        filter = {}

        # last 24 hours
        if interval == "1d":
            filter = {
                "updatedTime": {
                    "$lt": datetime.now().timestamp(),
                    "$gte": (datetime.now() - timedelta(days=1)).timestamp()
                }
            }

        balance = list(app.db.assets.find(filter).sort([("_id", -1)]))
        if balance:
            resp = jsonResp({"data": balance}, 200)
        return resp
