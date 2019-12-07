from dotenv import load_dotenv
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

load_dotenv()

class Orders():

  recvWindow = 10000

  def __init__(self, symbol):
        
    self.key = os.getenv("BINANCE_KEY")
    self.secret = os.getenv("BINANCE_SECRET")
    self.base_url = os.getenv("BASE")
    self.open_orders = os.getenv("OPEN_ORDERS")
    self.all_orders_url = os.getenv("ALL_ORDERS")
    self.order_url = os.getenv("ORDER")
    self.symbol = symbol
    # Buy order
    self.side = EnumDefinitions.order_side[0]
    # Required by API for Limit orders
    self.timeInForce = EnumDefinitions.time_in_force[0]

  def get_open_orders(self):
    timestamp = int(round(tm.time() * 1000))
    url = self.base_url + self.open_orders
    params = [
        ('symbol', self.symbol),
        ('timestamp', timestamp),
        ('recvWindow', self.recvWindow)
    ]
    res = requests.get(url=url, params=params)
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