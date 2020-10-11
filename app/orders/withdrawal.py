import hashlib
import hmac
import math
import sys
import time as tm
from urllib.parse import urlencode, urlparse

import numpy as np
import pandas as pd
import requests

from mailer import algo_notify
from utilities.api import EnumDefinitions
from utilities.environment import API_URL
from utilities.get_data import Ticker_Price, Exchange_Info
from utilities.indicators import bollinger_bands, macd, moving_average
from utilities.account import get_balances

base_url = API_URL.BINANCEAPI_BASE
withdraw_url = API_URL.BINANCE_WITHDRAW


class WITHDRAWAL_ORDER:
    """Post order

    Returns:
        [type] -- [description]
    """
    recvWindow = 10000
    key = API_URL.BINANCE_WAPI_KEY
    secret = API_URL.BINANCE_WAPI_SECRET
    name = 'coinbase-wallet'
    # Min amount to be considered for investing (BNB)
    min_funds = 0.000000

    def __init__(self, symbol):
        # symbol = asset
        self.symbol = symbol


    def find_max_funds(self):
        balances = get_balances(0.001)
        btc_symbols = []
        tp = Ticker_Price()
        for index, asset in enumerate(balances['asset'].values):
            if asset != 'BTC':
                asset_props = tp.request_data(asset+'BTC')
                asset_props['amount'] = balances.iloc[index]['free']
                asset_props['total'] = float(
                    asset_props['amount']) * float(asset_props['price'])
                btc_symbols.append(asset_props)

        if 'BTC' in balances['asset'].values:
            btc = {
                'symbol': 'BTCBTC',
                'amount': balances.loc[balances['asset'] == 'BTC', 'free'].values[-1],
                'price': 1,
                'total': balances.loc[balances['asset'] == 'BTC', 'free'].values[-1],
            }
            btc_symbols.append(btc)
        btc_symbols = pd.DataFrame(btc_symbols)
        biggest_asset = btc_symbols.loc[btc_symbols['total'].idxmax(
        ), 'symbol']
        return biggest_asset

    def get_available_funds(self):
        """Get available funds
        This function will always need already checked funds (asset must be available in funds)
        This check is done in find_max_funds()
        [returns] amount in quoteAsset
        """
        balances = get_balances(self.min_funds)
        max_fund = self.find_max_funds()
        ei = Exchange_Info()
        if (self.symbol.endswith(asset)):
            print('matched symbol {}'.format(self.symbol))
            return float(balances['free'][0])
        else:
            print('no symbol matched {}'.format(self.symbol))
            sys.exit(1)
            return None

    def compute_price(self):
        tp = Ticker_Price()
        data = tp.request_data(self.symbol)
        return float(data['price'])

    def compute_quantity_limit(self):
        funds = self.get_available_funds()
        return funds / self.compute_price()

    def compute_quantity(self):
        funds = self.get_available_funds()
        price = self.compute_price()
        return math.floor((funds / price))

    def compute_stop_price(self):
        pass
    
    def convert_symbol_asset(self):
        ie = Exchange_Info()
        asset = ie.find_quoteAsset(self.symbol)
        return asset

    def post_order(self):
        """Post Order: Market
        """
        order_type = EnumDefinitions.order_types[1]
        timestamp = int(round(tm.time() * 1000))
        url = base_url + withdraw_url
        # price = self.compute_price()
        # Margin 0.98 in case market price changes
        qty = self.compute_quantity()
        asset = self.convert_symbol_asset()
        # Get data for a single crypto e.g. BTT in BNB market
        params = [
            ('recvWindow', self.recvWindow),
            ('timestamp', timestamp),
            ('asset', asset),
            ('amount', qty),
            ('name', self.name)
        ]
        headers = {'X-MBX-APIKEY': self.key}

        # Prepare request for signing
        r = requests.Request('POST', url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(self.secret.encode('utf-8'), total_params.encode('utf-8'), hashlib.sha256).hexdigest()
        params.append(('signature', signature))

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        self.handle_error(res)

    def handle_error(self, req):
        try:
            req.raise_for_status()
            print('{} withdrawal complete'.format(self.symbol))
        except requests.exceptions.HTTPError as err:
            print('HTTPError: ', err.response.content, err)
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

