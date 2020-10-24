
import hashlib
import hmac
import os
import time as tm
from urllib.parse import urlparse

import requests
from flask import request, current_app as app
from main.tools.enum_definitions import EnumDefinitions
from main.tools.handle_error import handle_error
from main.tools.jsonresp import jsonResp
from main.account.models import Account

class Orders(Account):

    recvWindow = os.getenv("RECV_WINDOW")
    key = os.getenv("BINANCE_KEY")
    secret = os.getenv("BINANCE_SECRET")
    open_orders = os.getenv("OPEN_ORDERS")
    all_orders_url = os.getenv("ALL_ORDERS")
    order_url = os.getenv("ORDER")

    def __init__(self):

        # Buy order
        self.side = EnumDefinitions.order_side[0]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

    def get_all_orders(self):
        orders = list(app.db.orders.find({}))
        if orders:
            resp = jsonResp({"data": orders}, 200)
        else:
            resp = jsonResp({"message": "Orders not found!"}, 404)
        return resp

    def poll_historical_orders(self):
        url = self.all_orders_url
        symbols = self._exchange_info()["symbols"]
        for s in symbols:
            timestamp = int(round(tm.time() * 1000))
            params = [
                ('symbol', s["symbol"]),
                ('timestamp', timestamp),
                ('recvWindow', self.recvWindow)
            ]
            headers = {'X-MBX-APIKEY': self.key}

            # Prepare request for signing
            r = requests.Request(url=url, params=params, headers=headers)
            prepped = r.prepare()
            query_string = urlparse(prepped.url).query
            total_params = query_string

            # Generate and append signature
            signature = hmac.new(self.secret.encode(
                'utf-8'), total_params.encode('utf-8'), hashlib.sha256).hexdigest()
            params.append(('signature', signature))

            res = requests.get(url=url, params=params, headers=headers)
            handle_error(res)
            data = res.json()

            # Empty collection first
            app.db.orders.remove()

            # Check that we have no empty orders
            if (len(data) > 0):
                for o in data:
                    # Save in the DB
                    historical_orders = app.db.orders.save(o, {"$currentDate": {"createdAt": "true"}})

    def get_open_orders(self):
        timestamp = int(round(tm.time() * 1000))
        url = self.open_orders
        symbol = request.view_args["symbol"]
        params = [
            ('symbol', symbol),
            ('timestamp', timestamp),
            ('recvWindow', self.recvWindow)
        ]
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        return data

    def delete_order(self):
        timestamp = int(round(tm.time() * 1000))
        url = self.order_url
        # query params -> args
        # path params -> view_args
        symbol = request.args["symbol"]
        orderId = request.args["orderId"]
        params = [
            ('symbol', symbol),
            ('timestamp', timestamp),
            ('recvWindow', self.recvWindow),
            ('orderId', orderId),
        ]

        headers = {'X-MBX-APIKEY': self.key}

        # Prepare request for signing
        r = requests.Request(url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(self.secret.encode(
            'utf-8'), total_params.encode('utf-8'), hashlib.sha256).hexdigest()
        params.append(('signature', signature))

        # Response after request
        res = requests.delete(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data
