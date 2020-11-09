
import hashlib
import hmac
import os
import time as tm
from urllib.parse import urlparse

import requests
from flask import request, current_app as app
from api.tools.enum_definitions import EnumDefinitions
from api.tools.handle_error import handle_error
from api.tools.jsonresp import jsonResp, jsonResp_message
from api.account.models import Account
from api.tools.round_numbers import round_numbers

poll_percentage = 0

class Orders(Account):

    recvWindow = os.getenv("RECV_WINDOW")
    key = os.getenv("BINANCE_KEY")
    secret = os.getenv("BINANCE_SECRET")
    open_orders = os.getenv("OPEN_ORDERS")
    delete_open_orders = os.getenv("ALL_OPEN_ORDERS")
    all_orders_url = os.getenv("ALL_ORDERS")
    order_url = os.getenv("ORDER")

    def __init__(self):

        # Buy order
        self.side = EnumDefinitions.order_side[0]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

    def get_all_orders(self):
        # here we want to get the value of user (i.e. ?user=some-value)
        limit = int(request.args.get('limit'))
        offset = int(request.args.get('offset'))
        pages = app.db.orders.count()
        status = request.args.get('status', None)

        # Filters
        args = {}
        if status:
            args["status"] = status

        orders = list(app.db.orders.find(args).sort([("updateTime", -1)]).skip(offset).limit(limit))
        if orders:
            resp = jsonResp({"data": orders, "pages": pages}, 200)
        else:
            resp = jsonResp({"message": "Orders not found!"}, 404)
        return resp

    def poll_historical_orders(self):
        global poll_percentage
        url = self.all_orders_url
        symbols = self._exchange_info()["symbols"]
        symbols_count = len(symbols)

        # Empty collection first
        app.db.orders.remove()

        # Check if there are any polls in progress
        if poll_percentage > 0:
            resp = jsonResp({"message": "Polling in progress", "progress": f"{poll_percentage}"}, 200)
            return resp
        for i in range(symbols_count):

            timestamp = int(round(tm.time() * 1000))
            params = [
                ('symbol', symbols[i]["symbol"]),
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

            # Check that we have no empty orders
            if (len(data) > 0):
                for o in data:
                    # Save in the DB
                    app.db.orders.save(o, {"$currentDate": {"createdAt": "true"}})
                    if i == (symbols_count - 1):
                        poll_percentage = 0
                    else:
                        poll_percentage = round_numbers((i/symbols_count) * 100, 0)
            print(poll_percentage)
        resp = jsonResp({"message": "Polling finished!"}, 200)
        return resp

    def get_open_orders(self):
        timestamp = int(round(tm.time() * 1000))
        url = self.open_orders
        params = [
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

        if (len(data) > 0):
            resp = jsonResp({"message": "Open orders found!", "data": data}, 200)
        else:
            resp = jsonResp_message("No open orders found!", 200)
        return resp

    def delete_order(self):
        """
        Cancels single order by symbol
        - Optimal for open orders table
        """
        timestamp = int(round(tm.time() * 1000))
        url = self.order_url
        symbol = request.view_args["symbol"]
        orderId = request.view_args["orderid"]
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

        if (len(data) > 0):
            resp = jsonResp({"message": "Order deleted!", "data": data}, 200)
        else:
            resp = jsonResp_message("Failed to delete order", 200)
        return resp

    def delete_all_orders(self):
        """
        Delete All orders by symbol
        - Optimal for open orders table
        """
        symbol = request.args["symbol"]
        timestamp = int(round(tm.time() * 1000))
        url = self.open_orders
        # query params -> args
        # path params -> view_args
        symbol = request.args["symbol"]
        params = [
            ('symbol', symbol),
            ('timestamp', timestamp),
            ('recvWindow', self.recvWindow),
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

        if (len(data) > 0):
            resp = jsonResp({"message": "Orders deleted", "data": data}, 200)
        else:
            resp = jsonResp_message("No open orders found!", 200)
        return resp