import hashlib
import hmac
import json
import os
import time as tm
from urllib.parse import urlparse

import pandas as pd
import requests
from flask import current_app as app, request
from api.tools.handle_error import handle_error
from api.tools.jsonresp import jsonResp, jsonResp_message
from api.tools.round_numbers import proper_round
from api.tools.ticker import Conversion
from datetime import datetime, timedelta, date, time

class Account:

    recvWindow = os.getenv("RECV_WINDOW")
    secret = os.getenv('BINANCE_SECRET')
    key = os.getenv('BINANCE_KEY')
    account_url = os.getenv('ACCOUNT')
    exchangeinfo_url = os.getenv('EXCHANGE_INFO')
    ticker_price = os.getenv('TICKER_PRICE')
    ticker24_url = os.getenv('TICKER24')

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

    def ticker(self):
        url = self.ticker_price
        symbol = request.view_args["symbol"]
        params = {}
        if symbol:
            params = {'symbol': symbol}
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        resp = jsonResp({"data": data}, 200)
        return resp

    def get_ticker_price(self, symbol):
        url = self.ticker_price
        params = None
        if symbol:
            params = {'symbol': symbol}
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        return data["price"]

    def ticker_24(self):
        url = self.ticker24_url
        symbol = request.view_args["symbol"]
        params = {'symbol': symbol}
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        resp = jsonResp({"data": data}, 200)
        return resp

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

    def find_market(self, quote):
        symbols = self._exchange_info()["symbols"]
        market = next((s for s in symbols if s["baseAsset"] == quote), None)["symbol"]
        return market

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


class Assets(Account, Conversion):

    def __init__(self, app=None):
        self.usd_balance = 0
        self.app = app

    def get_usd_balance(self):
        """
        Cronjob that stores balances with its approximate current value in BTC
        """
        balances = self.get_balances().json
        current_time = datetime.now()
        total_usd = 0
        for b in balances:

            # Ordinary coins found in balance
            price = self.get_conversion(current_time, b["asset"])
            usd = b["free"] * float(price)
            total_usd += usd

        return proper_round(total_usd, 8)

    def get_pnl(self):
        index = int(request.args["days"])
        current_time = datetime.now()
        start = current_time - timedelta(days=7)

        if index:
            # data = list(app.db.balances.find({
            #     "time": {"$gte": start.timestamp() * 1000, "$lte": current_time.timestamp() * 1000},
            # }))
            data = list(app.db.balances.find({}))

        resp = jsonResp({"data": data}, 200)
        return resp

    def store_balance(self):
        """
        Alternative PnL data that runs as a cronjob everyday once at 1200
        Store current balance in Db
        """

        balances = self.get_balances().json
        current_time = current_time = datetime.now()
        total_btc = 0
        for b in balances:
            symbol = self.find_market(b["asset"])
            market = self.find_quoteAsset(symbol)
            if b["asset"] != "BTC":
                rate = self.get_ticker_price(symbol)
                if market != "BTC":
                    rate = self.get_ticker_price(market+"BTC")

            if "locked" in b:
                qty = b["free"] + b["locked"]
            else:
                qty = b["free"]

            btc_value = float(qty) * float(rate)

            # Only tether coins for hedging
            if b["asset"] == "USDT":
                rate = self.get_ticker_price("BTCUSDT")
                btc_value = float(qty) / float(rate)

            total_btc += btc_value

        total_usd = self.get_conversion(current_time, "BTC", "USD")
        balance = {
            "time": current_time,
            "estimated_total_btc": total_btc,
            "estimated_total_usd": total_usd
        }
        balanceId = self.app.db.balances.insert_one(balance, {"$currentDate": {"createdAt": "true"}})
        if balanceId:
            print(f"Balance stored! {current_time}")

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
