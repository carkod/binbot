from socketIO_client import SocketIO, BaseNamespace
import os
import logging
from websocket import create_connection
import json
from time import time
import requests
import hashlib
from urllib.parse import urlparse
import hmac
from main.tools import handle_error

class OrderUpdates(BaseNamespace):
    def __init__(self):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.base_url = os.getenv("BASE")
        self.ws_base_url = os.getenv("WS_BASE")
        self.user_datastream_listenkey = os.getenv("USER_DATA_STREAM")
        self.all_orders_url = os.getenv("ALL_ORDERS")
        self.order_url = os.getenv("ORDER")

        # streams
        self.host = os.getenv('WS_BASE')
        self.port = os.getenv('WS_BASE_PORT')
        self.path = '/ws'
        

    def get_listenkey(self):
        url = self.base_url + self.user_datastream_listenkey

        # Get data for a single crypto e.g. BTT in BNB market
        params = []
        headers = {'X-MBX-APIKEY': self.key}
        url = self.base_url + self.user_datastream_listenkey

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data

    
    def open_stream(self):
        url = self.host + ':' + self.port + self.path
        ws = create_connection(url)
        subscribe = json.dumps({
            "method": "SUBSCRIBE",
            "params": ['executionReport'],
            "id": 1
        }) 
        ws.send(subscribe)
        result =  ws.recv()
        result = json.loads(result)
        if result["result"] == None:
            print("Received '%s'" % result)
            return True
        # ws.close()
        return False
        # data = ws.recv_data()
        

    def get_stream(self, listenkey):
        url = self.host + ':' + self.port + self.path + '/' + listenkey
        ws = create_connection(url)
        result =  ws.recv()
        result = json.loads(result)
        return result
        