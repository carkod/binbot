from flask import Flask, request
from flask import current_app as app
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
from main.tools import EnumDefinitions, handle_error 
from main.account import Account


class Buy_Order(Account):
    """Post order

    Returns:
        [type] -- [description]
    """
    recvWindow = 10000
    # Min amount to be considered for investing (BNB)
    min_funds = 0.000000

    def __init__(self, symbol):
        self.key = app.config['KEY']
        self.secret = app.config['SECRET']
        self.base_url = app.config['BASE']
        self.order_url = app.config['ORDER']
        self.order_book_url = app.config['ORDER_BOOK']
        self.symbol = symbol
        # Buy order
        self.side = EnumDefinitions.order_side[0]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

    def get_balances(self):
        data = json.loads(Account().get_balances().data)['data']
        available_balance = 0
        for i in range(len(data)):
            if data[i]['asset'] == 'BTC':
                available_balance = data[i]['free']
                return available_balance
        return available_balance

    def last_order_book_price(self):
        url = self.base_url + self.order_book_url
        limit = 5
        params = [
          ('symbol', self.symbol),
          ('limit', limit),
        ]
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        return data


    # def compute_price(self):
    #     tp = Ticker_Price()
    #     data = tp.request_data(self.symbol)
    #     return float(data['price'])

    # def compute_quantity_limit(self):
    #     funds = self.get_available_funds()
    #     return funds / self.compute_price()

    # def compute_quantity(self):
    #     funds = self.get_available_funds()
    #     price = self.compute_price()
    #     return math.floor((funds / price))

    # def compute_stop_price(self):
    #     pass

    # def post_order_limit(self):
    #     # Limit order
    #     type = EnumDefinitions.order_types[0]
    #     timestamp = int(round(tm.time() * 1000))
    #     url = self.base_url + self.order_url
    #     price = self.compute_price()
    #     qty = int(self.compute_quantity_limit() * 100) / 100
    #     # Get data for a single crypto e.g. BTT in BNB market
    #     params = [
    #         ('recvWindow', self.recvWindow),
    #         ('timestamp', timestamp),
    #         ('symbol', self.symbol),
    #         ('side', self.side),
    #         ('type', type),
    #         ('timeInForce', self.timeInForce),
    #         ('price', price),
    #         ('quantity', qty)
    #     ]
    #     headers = {'X-MBX-APIKEY': self.key}

    #     # Prepare request for signing
    #     r = requests.Request('POST', url=url, params=params, headers=headers)
    #     prepped = r.prepare()
    #     query_string = urlparse(prepped.url).query
    #     total_params = query_string

    #     # Generate and append signature
    #     signature = hmac.new(self.secret.encode(
    #         'utf-8'), total_params.encode('utf-8'), hashlib.sha256).hexdigest()
    #     params.append(('signature', signature))

    #     # Response after request
    #     res = requests.post(url=url, params=params, headers=headers)
    #     handle_error(res)



class SELL_ORDER:
    """Post order

    Returns:
        [type] -- [description]
    """
    timestamp = int(round(tm.time() * 1000))
    recvWindow = 10000
    # Min amount to be considered for investing (BNB)
    min_funds = 0.000000

    def __init__(self, symbol):
        self.key = app.config['KEY']
        self.secret = app.config['SECRET']
        self.base_url = app.config['BASE']
        self.order_url = app.config['ORDER']

        self.symbol = symbol
        # Sell order
        self.side = EnumDefinitions.order_side[1]
        # Market order
        self.type = EnumDefinitions.order_types[1]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

    def get_available_funds(self):
        """1. Get funds available [array]
        2. Match funds with market Base coins (ETH, BNB, BTC...)
        3. Buy coins using the currency with highest amount
        [returns] amount in quoteAsset
        """
        balances = get_balances(self.min_funds)
        ei = Exchange_Info()
        symbols = ei.get_symbols()
        # symbols.drop(['baseAssetPrecision','status','orderTypes','icebergAllowed', 'isSpotTradingAllowed','isMarginTradingAllowed'], inplace=True, axis=1)
        base_asset = symbols.loc[symbols['symbol'] == self.symbol]['baseAsset']
        base_asset = base_asset.values[-1]
        balances_arr = pd.Series(balances['asset'])
        if (balances_arr.str.contains(base_asset)).any():
            print('matched symbol in funds {}'.format(self.symbol))
            return float(balances.loc[balances['asset'] == base_asset, 'free'].values[-1])
        else:
            print('no symbol matched {}'.format(self.symbol))
            sys.exit(1)
            return None

    def compute_price(self):
        tp = Ticker_Price()
        data = tp.request_data(self.symbol)
        return float(data['price'])

    def compute_quantity(self):
        funds = self.get_available_funds()
        return math.floor(funds)

    def compute_stop_price(self):
        pass

    def post_order_limit(self):
        url = base_url + order_url
        timestamp = int(round(tm.time() * 1000))
        price = self.compute_price()
        # round 5 numbers (10000)
        qty = int(self.compute_quantity() * 100) / 100
        # Get data for a single crypto e.g. BTT in BNB market
        params = [
            ('recvWindow', self.recvWindow),
            ('timestamp', timestamp),
            ('symbol', self.symbol),
            ('side', self.side),
            ('type', self.type),
            ('timeInForce', self.timeInForce),
            ('price', price),
            ('quantity', qty)
        ]
        headers = {'X-MBX-APIKEY': self.key}

        # Prepare request for signing
        r = requests.Request('POST', url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(self.secret.encode(
            'utf-8'), total_params.encode('utf-8'), hashlib.sha256).hexdigest()
        params.append(('signature', signature))

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        self.handle_error(res)

    def post_order(self):
        url = base_url + order_url
        timestamp = int(round(tm.time() * 1000))
        # round 5 numbers (10000)
        qty = int(self.compute_quantity() * 1000) / 1000
        # Get data for a single crypto e.g. BTT in BNB market
        params = [
            ('recvWindow', self.recvWindow),
            ('timestamp', timestamp),
            ('symbol', self.symbol),
            ('side', self.side),
            ('type', self.type),
            ('quantity', qty)
        ]
        headers = {'X-MBX-APIKEY': self.key}

        # Prepare request for signing
        r = requests.Request('POST', url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(self.secret.encode(
            'utf-8'), total_params.encode('utf-8'), hashlib.sha256).hexdigest()
        params.append(('signature', signature))

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        self.handle_error(res)

    
