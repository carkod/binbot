 
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
import os

 

class Orders():

  recvWindow = 10000

  def __init__(self):
        
    self.key = os.getenv("BINANCE_KEY")
    self.secret = os.getenv("BINANCE_SECRET")
    self.base_url = os.getenv("BASE")
    self.open_orders = os.getenv("OPEN_ORDERS")
    self.all_orders_url = os.getenv("ALL_ORDERS")
    self.order_url = os.getenv("ORDER")
    # Buy order
    self.side = EnumDefinitions.order_side[0]
    # Required by API for Limit orders
    self.timeInForce = EnumDefinitions.time_in_force[0]

  def get_open_orders(self):
    timestamp = int(round(tm.time() * 1000))
    url = self.base_url + self.open_orders
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
    url = self.base_url + self.order_url
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

  def get_single_order(self):
    pass


  """
  This Binance API is not very useful
  As it doesn't return all orders (higher weight, risk of ban)
  Think of a way to return all orders that have been held as an asset
  """
  def get_all_orders(self):
    pass